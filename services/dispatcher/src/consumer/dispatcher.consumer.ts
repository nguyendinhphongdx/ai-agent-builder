import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { RabbitSubscribe, Nack, AmqpConnection } from '@golevelup/nestjs-rabbitmq';
import {
  DispatchMessage,
  DispatchMessageWithMeta,
} from '../dispatch/dispatch.types';
import { routingKeyFor } from '../dispatch/queue-resolver';
import { ServiceRegistry } from '../config/service-registry';
import { HttpClientService } from '../services/http-client.service';
import { DispatchLogger, DispatchType } from '../utils/dispatch-logger';

const DISPATCHER_EXCHANGE = 'dispatcher';
const DISPATCHER_RETRY_EXCHANGE = 'dispatcher.retry';

const QUEUE_OPTIONS = {
  durable: true,
  arguments: {
    'x-dead-letter-exchange': DISPATCHER_EXCHANGE,
    'x-dead-letter-routing-key': 'dispatcher.dlq',
  },
};

/**
 * Dispatcher Consumer
 *
 * Subscribes to workload queues (mail, heavy, webhook, default). Each handler
 * delegates to the shared `processMessage` which:
 * 1. Calls the target service via HTTP
 * 2. On success → ack
 * 3. On failure within retry budget → republish to delayed retry queue (TTL-based)
 * 4. On exhausted retries → nack (message flows to DLQ via queue DLX config)
 *
 * Retry reliability: uses `dispatcher.retry` holding queue with per-message TTL.
 * Dead-lettered back to main exchange preserving original routing key. Survives
 * broker restarts — no in-process setTimeout.
 */
@Injectable()
export class DispatcherConsumer {
  private readonly logger = new DispatchLogger('DispatcherConsumer');
  private readonly defaultMaxAttempts: number;
  private readonly defaultBackoffMs: number;
  private readonly defaultBackoffMultiplier: number;

  constructor(
    private readonly serviceRegistry: ServiceRegistry,
    private readonly httpClient: HttpClientService,
    private readonly configService: ConfigService,
    private readonly amqpConnection: AmqpConnection,
  ) {
    this.defaultMaxAttempts = this.configService.get('RETRY_MAX_ATTEMPTS', 3);
    this.defaultBackoffMs = this.configService.get('RETRY_BACKOFF_MS', 1000);
    this.defaultBackoffMultiplier = this.configService.get(
      'RETRY_BACKOFF_MULTIPLIER',
      2,
    );
  }

  @RabbitSubscribe({
    exchange: DISPATCHER_EXCHANGE,
    routingKey: 'mail.dispatch',
    queue: 'dispatcher.mail',
    queueOptions: QUEUE_OPTIONS,
  })
  async handleMail(message: DispatchMessage | DispatchMessageWithMeta): Promise<void | Nack> {
    return this.processMessage(message);
  }

  @RabbitSubscribe({
    exchange: DISPATCHER_EXCHANGE,
    routingKey: 'heavy.dispatch',
    queue: 'dispatcher.heavy',
    queueOptions: QUEUE_OPTIONS,
  })
  async handleHeavy(message: DispatchMessage | DispatchMessageWithMeta): Promise<void | Nack> {
    return this.processMessage(message);
  }

  @RabbitSubscribe({
    exchange: DISPATCHER_EXCHANGE,
    routingKey: 'webhook.dispatch',
    queue: 'dispatcher.webhook',
    queueOptions: QUEUE_OPTIONS,
  })
  async handleWebhook(message: DispatchMessage | DispatchMessageWithMeta): Promise<void | Nack> {
    return this.processMessage(message);
  }

  @RabbitSubscribe({
    exchange: DISPATCHER_EXCHANGE,
    routingKey: 'default.dispatch',
    queue: 'dispatcher.default',
    queueOptions: QUEUE_OPTIONS,
  })
  async handleDefault(message: DispatchMessage | DispatchMessageWithMeta): Promise<void | Nack> {
    return this.processMessage(message);
  }

  private async processMessage(
    message: DispatchMessage | DispatchMessageWithMeta,
  ): Promise<void | Nack> {
    const meta = this.getOrInitMeta(message);
    const maxAttempts = message.retry?.maxAttempts || this.defaultMaxAttempts;
    const type: DispatchType = message.url ? 'WEBHOOK' : 'INTERNAL';
    const startTime = Date.now();

    this.logger.incoming({
      type,
      messageId: message.id,
      source: message.source,
      target: message.target,
      url: message.url,
      method: message.method,
      path: message.path,
      event: message.event,
      correlationId: message.correlationId,
      attempt: meta.attempt,
      maxAttempts,
    });

    try {
      const url = this.resolveUrl(message);
      const serviceHeaders = message.target
        ? this.serviceRegistry.getForwardHeaders(message.target)
        : {};
      const response = await this.httpClient.request(url, message, serviceHeaders);
      const duration = Date.now() - startTime;

      if (response.success) {
        this.logger.success({
          type,
          source: message.source,
          target: message.target,
          url: message.url,
          method: message.method,
          path: message.path,
          status: response.status,
          duration,
        });
        return;
      }

      return this.handleFailure(message, meta, maxAttempts, type, response.error);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      return this.handleFailure(message, meta, maxAttempts, type, errorMessage);
    }
  }

  private async handleFailure(
    message: DispatchMessage,
    meta: DispatchMessageWithMeta['_meta'],
    maxAttempts: number,
    type: DispatchType,
    error?: string,
  ): Promise<Nack> {
    if (meta.attempt < maxAttempts) {
      const delay = this.computeBackoff(message, meta.attempt);

      this.logger.retry({
        type,
        source: message.source,
        target: message.target,
        url: message.url,
        method: message.method,
        path: message.path,
        event: message.event,
        attempt: meta.attempt,
        maxAttempts,
        nextRetryIn: `${delay}ms`,
        error,
      });

      await this.scheduleRetry(message, meta, delay, error);
      // Ack original — retry lives in holding queue now
      return new Nack(false);
    }

    this.logger.failure({
      type,
      source: message.source,
      target: message.target,
      url: message.url,
      method: message.method,
      path: message.path,
      event: message.event,
      attempt: meta.attempt,
      maxAttempts,
      error: `Max retries exceeded. Last error: ${error}`,
    });

    // No requeue — queue DLX config forwards to dispatcher.dlq
    return new Nack(false);
  }

  private computeBackoff(message: DispatchMessage, attempt: number): number {
    const backoffMs = message.retry?.backoffMs || this.defaultBackoffMs;
    const multiplier = message.retry?.backoffMultiplier || this.defaultBackoffMultiplier;
    return backoffMs * Math.pow(multiplier, attempt - 1);
  }

  /**
   * Publish message to retry holding queue with per-message TTL. When TTL expires,
   * RabbitMQ dead-letters the message back to `dispatcher` exchange preserving its
   * original routing key → lands in the original workload queue for reprocessing.
   *
   * This is reliable across broker/consumer restarts (setTimeout was not).
   */
  private async scheduleRetry(
    message: DispatchMessage,
    meta: DispatchMessageWithMeta['_meta'],
    delay: number,
    lastError?: string,
  ): Promise<void> {
    const retryMessage: DispatchMessageWithMeta = {
      ...message,
      _meta: { ...meta, lastError },
    };

    // Route key = original workload routing key. After TTL this becomes the
    // routing key on the dead-letter back to main exchange.
    const originalRoutingKey = routingKeyFor(message.queue);

    try {
      await this.amqpConnection.publish(
        DISPATCHER_RETRY_EXCHANGE,
        originalRoutingKey,
        retryMessage,
        {
          persistent: true,
          expiration: String(delay),
        },
      );
    } catch (err) {
      this.logger.failure({
        type: message.url ? 'WEBHOOK' : 'INTERNAL',
        source: message.source,
        target: message.target,
        url: message.url,
        method: message.method,
        error: `Failed to schedule retry: ${err instanceof Error ? err.message : err}`,
      });
    }
  }

  private resolveUrl(message: DispatchMessage): string {
    if (message.url) return message.url;
    if (message.target && message.path) {
      return this.serviceRegistry.buildUrl(message.target, message.path);
    }
    throw new Error(
      `Invalid message: must have either 'url' or ('target' + 'path'). ID: ${message.id}`,
    );
  }

  private getOrInitMeta(
    message: DispatchMessage | DispatchMessageWithMeta,
  ): DispatchMessageWithMeta['_meta'] {
    if ('_meta' in message && message._meta) {
      return {
        ...message._meta,
        attempt: message._meta.attempt + 1,
        lastAttemptAt: new Date().toISOString(),
      };
    }
    return {
      attempt: 1,
      firstAttemptAt: new Date().toISOString(),
    };
  }
}
