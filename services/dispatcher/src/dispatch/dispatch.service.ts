import { Injectable, Logger } from '@nestjs/common';
import { AmqpConnection } from '@golevelup/nestjs-rabbitmq';
import axios from 'axios';
import * as https from 'https';
import { IncomingMessage } from 'http';
import { ServiceRegistry } from '../config/service-registry';
import {
  ExchangeRequest,
  ExchangeResponse,
  InternalRequest,
  WebhookRequest,
  StreamRequest,
  DispatchMessage,
} from './dispatch.types';
import {
  resolveInternalQueue,
  resolveWebhookQueue,
  routingKeyFor,
} from './queue-resolver';

const DISPATCHER_EXCHANGE = 'dispatcher';

const httpsAgent = new https.Agent({ rejectUnauthorized: false });

@Injectable()
export class DispatchService {
  private readonly logger = new Logger(DispatchService.name);

  constructor(
    private readonly amqpConnection: AmqpConnection,
    private readonly serviceRegistry: ServiceRegistry,
  ) {}

  async exchange(request: ExchangeRequest): Promise<ExchangeResponse> {
    const url = this.serviceRegistry.buildUrl(request.target, request.path);
    const method = (request.method || 'GET').toLowerCase();

    try {
      const response = await axios({
        method,
        url,
        data: request.body,
        headers: {
          'Content-Type': 'application/json',
          ...request.headers,
          'x-source-service': request.source || 'dispatcher',
        },
        timeout: request.timeout || 30000,
        validateStatus: () => true,
        httpsAgent,
      });

      return {
        status: response.status,
        data: response.data,
        headers: response.headers as Record<string, string>,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      this.logger.error(`Exchange failed: ${message}`);
      return { status: 500, data: { error: message } };
    }
  }

  async queueInternal(messageId: string, request: InternalRequest): Promise<void> {
    const queue = resolveInternalQueue(request.target, request.priority);

    const message: DispatchMessage = {
      id: messageId,
      target: request.target,
      path: request.path,
      method: request.method || 'POST',
      body: request.body,
      headers: request.headers,
      timeout: request.timeout,
      source: request.source,
      event: request.event,
      correlationId: request.correlationId,
      timestamp: new Date().toISOString(),
      retry: request.retry,
      queue,
    };

    await this.publish(message);
  }

  async queueWebhook(messageId: string, request: WebhookRequest): Promise<void> {
    const message: DispatchMessage = {
      id: messageId,
      url: request.url,
      method: request.method || 'POST',
      body: request.body,
      headers: request.headers,
      timeout: request.timeout,
      source: request.source,
      event: request.event,
      correlationId: request.correlationId,
      timestamp: new Date().toISOString(),
      retry: request.retry,
      queue: resolveWebhookQueue(),
    };

    await this.publish(message);
  }

  async streamProxy(request: StreamRequest): Promise<IncomingMessage> {
    const url = this.serviceRegistry.buildUrl(request.target, request.path);
    const method = (request.method || 'POST').toLowerCase();

    const response = await axios({
      method,
      url,
      data: request.body,
      headers: {
        'Content-Type': 'application/json',
        ...request.headers,
        'x-source-service': request.source || 'dispatcher',
      },
      timeout: request.timeout || 120000,
      responseType: 'stream',
      httpsAgent,
    });

    return response.data as IncomingMessage;
  }

  private async publish(message: DispatchMessage): Promise<void> {
    const routingKey = routingKeyFor(message.queue);
    await this.amqpConnection.publish(
      DISPATCHER_EXCHANGE,
      routingKey,
      message,
      { persistent: true },
    );
  }
}
