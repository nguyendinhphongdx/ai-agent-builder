/**
 * Dispatch Types — AgentForge internal dispatcher
 */

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

/**
 * Known internal services. Resolved to URLs via ServiceRegistry (routes.json).
 * New services: add to routes.json + this union.
 */
export type ServiceName = 'backend' | 'mail' | 'socket' | 'code-sandbox';

/**
 * Internal RabbitMQ queues. Dispatcher auto-picks one based on target + priority;
 * clients do NOT pass this.
 */
export type DispatchQueue = 'mail' | 'heavy' | 'webhook' | 'default';
export const DEFINED_QUEUES: DispatchQueue[] = ['mail', 'heavy', 'webhook', 'default'];

/**
 * Priority hint for async dispatch. Currently affects queue routing only
 * (low → default batch queue). Does not set AMQP message priority.
 */
export type Priority = 'low' | 'normal' | 'high';

export interface RetryConfig {
  maxAttempts?: number;
  backoffMs?: number;
  backoffMultiplier?: number;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sync exchange
// ─────────────────────────────────────────────────────────────────────────────

export interface ExchangeRequest {
  target: ServiceName;
  path: string;
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  timeout?: number;
  source?: string;
}

export interface ExchangeResponse<T = unknown> {
  status: number;
  data: T;
  headers?: Record<string, string>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Async internal (service → service via RabbitMQ)
// ─────────────────────────────────────────────────────────────────────────────

export interface InternalRequest {
  target: ServiceName;
  path: string;
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  timeout?: number;
  source: string;
  event: string;
  correlationId?: string;
  retry?: RetryConfig;
  priority?: Priority;
}

export interface InternalResponse {
  success: true;
  messageId: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Async webhook (external URL)
// ─────────────────────────────────────────────────────────────────────────────

export interface WebhookRequest {
  url: string;
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  timeout?: number;
  source: string;
  event: string;
  correlationId?: string;
  retry?: RetryConfig;
  priority?: Priority;
}

export interface WebhookResponse {
  success: true;
  messageId: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// SSE stream proxy
// ─────────────────────────────────────────────────────────────────────────────

export interface StreamRequest {
  target: ServiceName;
  path: string;
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  timeout?: number;
  source?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Internal queue message (not exposed in HTTP API)
// ─────────────────────────────────────────────────────────────────────────────

export interface DispatchMessage {
  id: string;
  correlationId?: string;
  target?: ServiceName;
  path?: string;
  url?: string;
  method: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  timeout?: number;
  source: string;
  event: string;
  timestamp: string;
  retry?: RetryConfig;
  queue: DispatchQueue;
}

export interface DispatchMessageWithMeta extends DispatchMessage {
  _meta: {
    attempt: number;
    firstAttemptAt: string;
    lastAttemptAt?: string;
    lastError?: string;
  };
}
