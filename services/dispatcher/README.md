# Dispatcher Service

Internal API gateway cho AgentForge — service-to-service calls không cần biết target host. Các service khác chỉ biết host của dispatcher, gọi qua HTTP với `target: 'mail' | 'backend' | 'socket' | 'code-sandbox'`.

## Why

Không có dispatcher, mỗi service phải tự config URL của 3 service còn lại → N×N env vars, khó thay đổi. Dispatcher:

- **Service discovery**: `routes.json` + env overrides, 1 chỗ duy nhất
- **3 exchange patterns** cho 3 nhu cầu khác nhau: sync / async / stream
- **Reliable retry** với RabbitMQ TTL-based delayed queue (không dùng `setTimeout`)
- **Auth** bằng shared secret để chặn request từ ngoài Docker network
- **Queue isolation**: mail bị chậm không ảnh hưởng code-sandbox

## Architecture

```text
┌─────────┐     ┌────────────────────────────────────────┐     ┌──────────┐
│ backend │────▶│  Dispatcher (port 3010)                │────▶│   mail   │
└─────────┘     │                                        │     └──────────┘
                │  POST /dispatch/exchange   → sync      │     ┌──────────┐
                │  POST /dispatch/stream     → SSE       │────▶│  socket  │
                │  POST /dispatch/internal   → async     │     └──────────┘
                │  POST /dispatch/webhook    → async     │     ┌──────────┐
                │                                        │────▶│code-sbx  │
                │  Auth: x-dispatcher-token              │     └──────────┘
                └──────┬─────────────────────────────────┘
                       │ async via RabbitMQ
                       ▼
        ┌──────────────────────────────────────────┐
        │ Exchange: dispatcher (topic)             │
        │                                          │
        │  mail.dispatch    → dispatcher.mail      │
        │  heavy.dispatch   → dispatcher.heavy     │
        │  webhook.dispatch → dispatcher.webhook   │
        │  default.dispatch → dispatcher.default   │
        │                                          │
        │  Exchange: dispatcher.retry (topic)      │
        │  # → dispatcher.retry (TTL holding)      │
        │    └─ DLX=dispatcher, preserve RK        │
        │                                          │
        │  Dead-letter: dispatcher.dlq             │
        └──────────────────────────────────────────┘
```

## Endpoints

### `POST /dispatch/exchange` — Sync HTTP proxy

Forward request đến target service, trả response:

```json
{
  "target": "backend",
  "path": "/api/users/me",
  "method": "GET",
  "timeout": 5000
}
```

Response:

```json
{
  "status": 200,
  "data": { "id": "...", "email": "..." },
  "headers": { "content-type": "application/json" }
}
```

### `POST /dispatch/stream` — SSE stream proxy

Pipe streaming response từ target (AI completion, log tail...):

```json
{
  "target": "code-sandbox",
  "path": "/execute/stream",
  "method": "POST",
  "body": { "code": "print(1)" },
  "timeout": 120000
}
```

Response headers: `text/event-stream`. Client disconnect (`res.close`) propagate lên upstream → target service tự huỷ.

### `POST /dispatch/internal` — Async internal call

Publish vào RabbitMQ, consumer gọi target. Fire & forget:

```json
{
  "target": "mail",
  "path": "/mail/send",
  "method": "POST",
  "body": { "to": "user@example.com", "subject": "Welcome" },
  "source": "backend",
  "event": "user.registered",
  "correlationId": "req-abc-123",
  "retry": { "maxAttempts": 5, "backoffMs": 2000 },
  "priority": "normal"
}
```

Response (`202 Accepted`):

```json
{ "success": true, "messageId": "uuid-v4" }
```

### `POST /dispatch/webhook` — Async external webhook

Giống `/internal` nhưng target là URL bên ngoài (partner webhooks):

```json
{
  "url": "https://partner.example.com/hook",
  "method": "POST",
  "body": { "event": "user.verified", "userId": "..." },
  "source": "backend",
  "event": "user.verified",
  "correlationId": "..."
}
```

## Queue routing

**Client KHÔNG chỉ định queue** — dispatcher tự pick dựa trên `target`:

| Target | Queue | Rationale |
| --- | --- | --- |
| `mail` | `mail` | Email I/O chậm + rate-limit bởi provider → isolate |
| `code-sandbox` | `heavy` | Tác vụ nặng, long-running |
| `backend` / `socket` | `default` | Fast I/O chung |
| webhook (external) | `webhook` | Partner endpoint không đáng tin, isolate |

Override bằng `priority: 'low'` → luôn rơi vào `default` (batch queue). `high` giữ nguyên target queue (future: map sang queue riêng với concurrency cao hơn).

## Reliable retry

Thay vì `setTimeout` in-process (mất message khi restart), dispatcher dùng **RabbitMQ TTL + DLX**:

1. Consumer xử lý fail → publish message vào `dispatcher.retry` queue với `expiration = backoffMs * multiplier^(attempt-1)`.
2. `dispatcher.retry` queue không có consumer — message nằm đó đợi TTL.
3. TTL hết → RabbitMQ dead-letters message về `dispatcher` exchange, **giữ nguyên routing key gốc** (`mail.dispatch` → `dispatcher.mail` queue).
4. Consumer xử lý lại với `_meta.attempt` tăng lên.
5. Hết retry budget → nack → queue DLX config forward về `dispatcher.dlq`.

Survive broker/consumer restart vì state nằm trong RabbitMQ.

## Auth

Set `DISPATCHER_SECRET` env var. Caller phải gửi:

```http
x-dispatcher-token: <secret>
```

hoặc `Authorization: Bearer <secret>`. Health endpoints (`/health`, `/healthz`, `/readyz`) bypass auth cho load balancer.

**Dev mode**: không set `DISPATCHER_SECRET` → guard disabled, service log warning. Không bao giờ deploy production không có secret.

So sánh bằng constant-time để chống timing attack ([dispatcher-auth.guard.ts](src/auth/dispatcher-auth.guard.ts)).

## Environment variables

| Biến | Mặc định | Mô tả |
| --- | --- | --- |
| `PORT` | `3010` | HTTP port |
| `NODE_ENV` | `development` | — |
| `DISPATCHER_SECRET` | *(unset)* | Shared secret. Unset = auth disabled (dev only) |
| `RABBITMQ_URL` | `amqp://agentforge:agentforge@localhost:5672` | AMQP connection |
| `HTTP_TIMEOUT` | `30000` | Default HTTP timeout cho consumer |
| `RETRY_MAX_ATTEMPTS` | `3` | Default retry budget |
| `RETRY_BACKOFF_MS` | `1000` | Initial backoff |
| `RETRY_BACKOFF_MULTIPLIER` | `2` | Exponential multiplier |
| `BACKEND_URL` | *(routes.json)* | Override URL for `backend` |
| `MAIL_URL` | *(routes.json)* | Override URL for `mail` |
| `SOCKET_URL` | *(routes.json)* | Override URL for `socket` |
| `CODE_SANDBOX_URL` | *(routes.json)* | Override URL for `code-sandbox` |

Format override: `{SERVICE_NAME}_URL` (hyphens → underscores). ENV có priority hơn [routes.json](src/config/routes.json).

## Thêm service mới

1. Thêm entry vào [src/config/routes.json](src/config/routes.json) với URL production mặc định.
2. Thêm vào `ServiceName` union trong [dispatch.types.ts](src/dispatch/dispatch.types.ts).
3. (Optional) Map queue workload trong [queue-resolver.ts](src/dispatch/queue-resolver.ts).
4. (Optional) Thêm env var override `{NAME}_URL` vào docker-compose.yml.

## Tracing headers

Dispatcher tự inject khi forward request:

- `x-source-service`: service nào gọi (lấy từ header caller hoặc body.source)
- `X-Dispatch-Id`: UUID của dispatch message (async only)
- `X-Dispatch-Event`: event name
- `X-Correlation-Id`: tracing across services (pass-through)

Target service đọc headers này để log/trace.

## Development

```bash
pnpm install
cp .env.example .env      # optional — dispatcher chạy được không cần .env nếu có RabbitMQ
pnpm dev                  # watch mode
pnpm build                # nest build
pnpm typecheck
```

## Docker

```bash
docker network create agentforge    # một lần
cd services/dispatcher
docker compose up -d
```

Service tự join network `agentforge` (external), resolve target container bằng container name (`agentforge-mail`, `agentforge-socket`...).
