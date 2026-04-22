import { Logger } from '@nestjs/common';

/**
 * Dispatch Logger Utility
 *
 * Pretty-prints dispatch events with clear source → target flow
 */

export type DispatchType = 'EXCHANGE' | 'STREAM' | 'INTERNAL' | 'WEBHOOK';
export type LogLevel = 'log' | 'warn' | 'error';

interface LogParams {
  type: DispatchType;
  source?: string;
  target?: string;
  url?: string;
  method: string;
  path?: string;
  event?: string;
  messageId?: string;
  status?: number;
  duration?: number;
  attempt?: number;
  maxAttempts?: number;
  error?: string;
  correlationId?: string;
}

const TYPE_LABELS: Record<DispatchType, { label: string; desc: string }> = {
  EXCHANGE: { label: 'EXCHANGE', desc: 'sync' },
  STREAM: { label: 'STREAM', desc: 'sse/proxy' },
  INTERNAL: { label: 'INTERNAL', desc: 'async/queue' },
  WEBHOOK: { label: 'WEBHOOK', desc: 'async/external' },
};

const ICONS = {
  arrow: '→',
  success: '✓',
  error: '✗',
  pending: '◎',
  retry: '↻',
};

export class DispatchLogger {
  private logger: Logger;

  constructor(context: string) {
    this.logger = new Logger(context);
  }

  /**
   * Log incoming request
   */
  incoming(params: LogParams): void {
    const typeInfo = TYPE_LABELS[params.type];
    const flow = this.formatFlow(params);
    const request = this.formatRequest(params);
    const meta = this.formatMeta(params);

    const lines = [
      `${ICONS.pending} ${typeInfo.label} (${typeInfo.desc})`,
      `   ${flow}`,
      `   ${request}`,
    ];

    if (meta) {
      lines.push(`   ${meta}`);
    }

    this.logger.log(lines.join('\n'));
  }

  /**
   * Log successful completion
   */
  success(params: LogParams): void {
    const typeInfo = TYPE_LABELS[params.type];
    const flow = this.formatFlow(params);
    const durationStr = params.duration ? ` (${params.duration}ms)` : '';
    const statusStr = params.status ? `${params.status}` : 'OK';

    this.logger.log(
      `${ICONS.success} ${typeInfo.label} | ${flow} | ${statusStr}${durationStr}`,
    );
  }

  /**
   * Log failure
   */
  failure(params: LogParams, level: LogLevel = 'error'): void {
    const typeInfo = TYPE_LABELS[params.type];
    const flow = this.formatFlow(params);
    const statusStr = params.status ? `${params.status}` : 'ERROR';
    const errorStr = params.error ? ` - ${params.error}` : '';
    const attemptStr =
      params.attempt && params.maxAttempts
        ? ` [${params.attempt}/${params.maxAttempts}]`
        : '';

    const message = `${ICONS.error} ${typeInfo.label} | ${flow} | ${statusStr}${attemptStr}${errorStr}`;

    if (level === 'warn') {
      this.logger.warn(message);
    } else {
      this.logger.error(message);
    }
  }

  /**
   * Log retry
   */
  retry(params: LogParams & { nextRetryIn: string }): void {
    const typeInfo = TYPE_LABELS[params.type];
    const flow = this.formatFlow(params);
    const attemptStr =
      params.attempt && params.maxAttempts
        ? `[${params.attempt}/${params.maxAttempts}]`
        : '';

    this.logger.warn(
      `${ICONS.retry} ${typeInfo.label} | ${flow} | Retry ${attemptStr} in ${params.nextRetryIn}`,
    );
  }

  /**
   * Log queued message
   */
  queued(params: LogParams): void {
    const typeInfo = TYPE_LABELS[params.type];
    const flow = this.formatFlow(params);
    const idStr = params.messageId ? ` [${params.messageId.slice(0, 8)}]` : '';
    const eventStr = params.event ? ` event=${params.event}` : '';

    this.logger.log(
      `${ICONS.pending} ${typeInfo.label} | ${flow} | Queued${idStr}${eventStr}`,
    );
  }

  /**
   * Format flow: source → target
   */
  private formatFlow(params: LogParams): string {
    const source = params.source || '(caller)';

    if (params.target) {
      return `${source} ${ICONS.arrow} ${params.target}`;
    }

    if (params.url) {
      // Extract host from URL
      try {
        const urlObj = new URL(params.url);
        return `${source} ${ICONS.arrow} ${urlObj.host}`;
      } catch {
        return `${source} ${ICONS.arrow} (external)`;
      }
    }

    return source;
  }

  /**
   * Format request: METHOD /path
   */
  private formatRequest(params: LogParams): string {
    const method = params.method || 'GET';

    if (params.path) {
      return `${method} ${params.path}`;
    }

    if (params.url) {
      try {
        const urlObj = new URL(params.url);
        return `${method} ${urlObj.pathname}`;
      } catch {
        return `${method} ${params.url}`;
      }
    }

    return method;
  }

  /**
   * Format metadata
   */
  private formatMeta(params: LogParams): string | null {
    const parts: string[] = [];

    if (params.attempt && params.maxAttempts) {
      parts.push(`attempt=${params.attempt}/${params.maxAttempts}`);
    }

    if (params.event) {
      parts.push(`event=${params.event}`);
    }

    if (params.messageId) {
      parts.push(`id=${params.messageId.slice(0, 8)}`);
    }

    if (params.correlationId) {
      parts.push(`corr=${params.correlationId.slice(0, 8)}`);
    }

    return parts.length > 0 ? parts.join(' | ') : null;
  }
}

// Singleton instance for convenience
export const dispatchLogger = new DispatchLogger('Dispatcher');
