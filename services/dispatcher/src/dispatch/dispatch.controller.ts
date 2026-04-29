import {
  BadRequestException,
  Controller,
  Post,
  Body,
  HttpCode,
  HttpStatus,
  Headers,
  Res,
  Header,
} from '@nestjs/common';
import { Response } from 'express';
import { v4 as uuid } from 'uuid';
import { DispatchService } from './dispatch.service';
import {
  ExchangeRequest,
  ExchangeResponse,
  InternalRequest,
  InternalResponse,
  WebhookRequest,
  WebhookResponse,
  StreamRequest,
} from './dispatch.types';
import { DispatchLogger } from '../utils/dispatch-logger';
import { assertSafeUrl } from '../utils/url-guard';

/**
 * Dispatch Controller
 *
 * 4 endpoints:
 * - POST /dispatch/exchange  — Sync HTTP proxy (internal service)
 * - POST /dispatch/stream    — SSE stream proxy (internal service)
 * - POST /dispatch/internal  — Async internal service call (via RabbitMQ)
 * - POST /dispatch/webhook   — Async external webhook (via RabbitMQ)
 *
 * Caller identity: `x-source-service` header OR `source` field in body.
 * Header takes precedence — body `source` is used as fallback for backward compat.
 */
@Controller('dispatch')
export class DispatchController {
  private readonly logger = new DispatchLogger('DispatchController');

  constructor(private readonly dispatchService: DispatchService) {}

  @Post('exchange')
  @HttpCode(HttpStatus.OK)
  async exchange(
    @Body() request: ExchangeRequest,
    @Headers('x-source-service') sourceHeader?: string,
  ): Promise<ExchangeResponse> {
    request.source = sourceHeader || request.source || 'unknown';
    const startTime = Date.now();

    this.logger.incoming({
      type: 'EXCHANGE',
      source: request.source,
      target: request.target,
      method: request.method || 'GET',
      path: request.path,
    });

    const response = await this.dispatchService.exchange(request);
    const duration = Date.now() - startTime;

    if (response.status >= 200 && response.status < 400) {
      this.logger.success({
        type: 'EXCHANGE',
        source: request.source,
        target: request.target,
        method: request.method || 'GET',
        path: request.path,
        status: response.status,
        duration,
      });
    } else {
      const data = response.data as Record<string, unknown> | null;
      this.logger.failure(
        {
          type: 'EXCHANGE',
          source: request.source,
          target: request.target,
          method: request.method || 'GET',
          path: request.path,
          status: response.status,
          error:
            (data && typeof data === 'object'
              ? data.message?.toString() ?? data.error?.toString()
              : undefined) ?? undefined,
        },
        'warn',
      );
    }

    return response;
  }

  @Post('stream')
  @Header('Content-Type', 'text/event-stream')
  @Header('Cache-Control', 'no-cache')
  @Header('Connection', 'keep-alive')
  async stream(
    @Body() request: StreamRequest,
    @Headers('x-source-service') sourceHeader?: string,
    @Res() res?: Response,
  ) {
    if (!res) return;

    request.source = sourceHeader || request.source || 'unknown';

    this.logger.incoming({
      type: 'STREAM',
      source: request.source,
      target: request.target,
      method: request.method || 'POST',
      path: request.path,
    });

    try {
      const upstream = await this.dispatchService.streamProxy(request);

      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');

      upstream.pipe(res);

      // Propagate client disconnect to upstream so we don't waste target service resources
      res.on('close', () => {
        if (!upstream.destroyed) upstream.destroy();
      });

      upstream.on('end', () => {
        this.logger.success({
          type: 'STREAM',
          source: request.source,
          target: request.target,
          method: request.method || 'POST',
          path: request.path,
          status: 200,
        });
      });

      upstream.on('error', (err: Error) => {
        this.logger.failure({
          type: 'STREAM',
          source: request.source,
          target: request.target,
          method: request.method || 'POST',
          path: request.path,
          error: err.message,
        });
        if (!res.writableEnded) {
          res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
          res.end();
        }
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      this.logger.failure({
        type: 'STREAM',
        source: request.source,
        target: request.target,
        method: request.method || 'POST',
        path: request.path,
        error: message,
      });
      res.status(500).json({ error: message });
    }
  }

  @Post('internal')
  @HttpCode(HttpStatus.ACCEPTED)
  async internal(
    @Body() request: InternalRequest,
    @Headers('x-source-service') sourceHeader?: string,
  ): Promise<InternalResponse> {
    request.source = sourceHeader || request.source;
    const messageId = uuid();

    this.logger.queued({
      type: 'INTERNAL',
      messageId,
      source: request.source,
      target: request.target,
      method: request.method || 'POST',
      path: request.path,
      event: request.event,
      correlationId: request.correlationId,
    });

    await this.dispatchService.queueInternal(messageId, request);
    return { success: true, messageId };
  }

  @Post('webhook')
  @HttpCode(HttpStatus.ACCEPTED)
  async webhook(
    @Body() request: WebhookRequest,
    @Headers('x-source-service') sourceHeader?: string,
  ): Promise<WebhookResponse> {
    request.source = sourceHeader || request.source;

    try {
      await assertSafeUrl(request.url);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Invalid URL';
      throw new BadRequestException(message);
    }

    const messageId = uuid();

    this.logger.queued({
      type: 'WEBHOOK',
      messageId,
      source: request.source,
      url: request.url,
      method: request.method || 'POST',
      event: request.event,
      correlationId: request.correlationId,
    });

    await this.dispatchService.queueWebhook(messageId, request);
    return { success: true, messageId };
  }
}
