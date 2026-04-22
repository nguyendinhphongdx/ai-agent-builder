import type { DispatchQueue, Priority, ServiceName } from './dispatch.types';

/**
 * Map target service → default queue. Groups by workload characteristics:
 * - mail: isolated so slow SendGrid doesn't block other work
 * - heavy: long-running tasks (code-sandbox exec, AI completions)
 * - default: everything else (backend, socket)
 */
const TARGET_QUEUE: Record<ServiceName, DispatchQueue> = {
  mail: 'mail',
  'code-sandbox': 'heavy',
  backend: 'default',
  socket: 'default',
};

/**
 * Resolve queue for an internal dispatch (target + path).
 * Priority can override — `high` stays on target queue, `low` always goes to default batch.
 */
export function resolveInternalQueue(
  target: ServiceName,
  priority: Priority = 'normal',
): DispatchQueue {
  if (priority === 'low') return 'default';
  return TARGET_QUEUE[target] ?? 'default';
}

/**
 * External webhooks always go to `webhook` queue — isolated from internal traffic
 * so a flaky partner endpoint doesn't starve internal retries.
 */
export function resolveWebhookQueue(): DispatchQueue {
  return 'webhook';
}

/**
 * Routing key convention: `<queue>.dispatch` → consumer subscribes to this.
 */
export function routingKeyFor(queue: DispatchQueue): string {
  return `${queue}.dispatch`;
}
