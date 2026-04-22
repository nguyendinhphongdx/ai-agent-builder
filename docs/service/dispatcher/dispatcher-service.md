---
id: service-dispatcher
title: Dispatcher Service
domain: service
tags: [dispatcher, api-gateway, rabbitmq, microservice, service-discovery, sse, retry, nestjs]
related: [service-mail, backend-auth]
summary: Internal API gateway on port 3010 that routes service-to-service calls. Supports sync HTTP proxy, async via RabbitMQ (mail / heavy / webhook / default queues with TTL-based reliable retry), and SSE stream proxy. Auth via shared secret.
---

# Dispatcher Service

## Overview

Dispatcher là internal API gateway — trung gian giữa các AgentForge services. Mục đích:

- **Service discovery một chỗ**: `routes.json` + env overrides; service khác chỉ cần biết host dispatcher.
- **3 exchange patterns**: sync (request/response), async (fire & forget qua RabbitMQ), SSE stream proxy.
- **Reliable retry** dùng RabbitMQ TTL+DLX (survive restart, không dùng `setTimeout`).
- **Queue isolation** theo loại workload — mail chậm không block code-sandbox.
- **Auth bằng shared secret** — chặn request từ ngoài internal network.

Source: [services/dispatcher/](../../../services/dispatcher/). Vận hành: [services/dispatcher/README.md](../../../services/dispatcher/README.md).

## Specification

### Runtime

| Attribute | Value |
| --- | --- |
| Framework | NestJS 10 (Node 20) |
| Port | `3010` |
| Container | `agentforge-dispatcher` |
| Network | `agentforge` (external) |
| Broker | RabbitMQ (`@golevelup/nestjs-rabbitmq`) |
| Memory limit | 256M |

### HTTP API

Tất cả endpoints (trừ health) yêu cầu header `x-dispatcher-token: <DISPATCHER_SECRET>` khi biến env được set.

| Endpoint | Type | Timeout default | Response |
| --- | --- | --- | --- |
| `POST /dispatch/exchange` | Sync HTTP proxy | 30s | `200 { status, data, headers }` |
| `POST /dispatch/stream` | SSE proxy | 120s | `text/event-stream` pipe |
| `POST /dispatch/internal` | Async (RabbitMQ) | — | `202 { success, messageId }` |
| `POST /dispatch/webhook` | Async external | — | `202 { success, messageId }` |
| `GET /health` | — | — | Full status + registered services |
| `GET /healthz`, `/readyz` | — | — | k8s probes |

Request shapes xem [dispatch.types.ts](../../../services/dispatcher/src/dispatch/dispatch.types.ts).

### Queue routing

Dispatcher **tự quyết queue** dựa trên `target` (hoặc URL cho webhook). Client không pass `queue` field — thay vào đó có optional `priority: 'low' | 'normal' | 'high'`.

Mapping ([queue-resolver.ts](../../../services/dispatcher/src/dispatch/queue-resolver.ts)):

| Target | Default queue | Routing key | Rationale |
| --- | --- | --- | --- |
| `mail` | `mail` | `mail.dispatch` | Email I/O chậm + provider rate-limit → isolate |
| `code-sandbox` | `heavy` | `heavy.dispatch` | Long-running execution |
| `backend` / `socket` | `default` | `default.dispatch` | Fast internal I/O |
| (webhook URL) | `webhook` | `webhook.dispatch` | Partner endpoint flaky, isolate từ internal |

`priority: 'low'` override về `default` (batch). `'high'` giữ target queue.

### Reliable retry via TTL + DLX

Scaffold ban đầu dùng `setTimeout` in-process → mất message khi service restart. Current design dùng RabbitMQ native delayed queue:

```text
[Consumer handleMail]
    │
    │ fail → handleFailure
    ▼
publish to "dispatcher.retry" exchange
RK = mail.dispatch (original)
options: { expiration: delayMs, persistent: true }
    │
    ▼
[dispatcher.retry queue]   ← no consumer
config: x-dead-letter-exchange = "dispatcher"
(no x-dead-letter-routing-key → preserves RK)
    │
    │ TTL expires (delayMs later)
    ▼
Dead-letter back to "dispatcher" exchange
with original RK "mail.dispatch"
    │
    ▼
[dispatcher.mail queue] → consumer handleMail (attempt++)
```

Thuộc tính:

- **Crash-safe**: retry state nằm trong RabbitMQ, không trong Node process.
- **Per-message TTL**: mỗi message có backoff riêng (`backoffMs * multiplier^(attempt-1)`).
- **Routing key preservation**: không cần maintain `dispatcher.{queue}.retry` per-queue — 1 retry queue cho tất cả.
- **DLQ flow**: khi hết `maxAttempts`, consumer nack → queue DLX config forward về `dispatcher.dlq`.

### Auth guard

[DispatcherAuthGuard](../../../services/dispatcher/src/auth/dispatcher-auth.guard.ts) là global `APP_GUARD`. Logic:

1. Nếu `DISPATCHER_SECRET` unset → guard disabled, log warning ở boot.
2. Health endpoints bypass.
3. Đọc token từ `x-dispatcher-token` header hoặc `Authorization: Bearer <token>`.
4. So sánh **constant-time** để tránh timing attack.

Không propagate secret sang target services — target tự validate `x-source-service` header nếu muốn.

### Service registry

[service-registry.ts](../../../services/dispatcher/src/config/service-registry.ts) load `routes.json` ở startup, env override theo format `{NAME}_URL` (hyphens → underscores).

Ví dụ: `code-sandbox` → `CODE_SANDBOX_URL`.

Priority: **env var > routes.json**.

### Tracing

Dispatcher inject headers khi forward:

| Header | Source | Purpose |
| --- | --- | --- |
| `x-source-service` | Header `x-source-service` của caller hoặc `body.source` | Target biết ai gọi |
| `X-Dispatch-Id` | UUID generate tại `/internal` và `/webhook` | Trace async message |
| `X-Dispatch-Event` | `body.event` | Grep logs theo event |
| `X-Correlation-Id` | `body.correlationId` (pass-through) | Tracing multi-hop |

## Integration

### Backend (Python) gọi sync

```python
import httpx

async def get_user_profile(user_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://agentforge-dispatcher:3010/dispatch/exchange",
            headers={
                "x-dispatcher-token": os.environ["DISPATCHER_SECRET"],
                "x-source-service": "backend",
            },
            json={
                "target": "backend",
                "path": f"/api/users/{user_id}",
                "method": "GET",
            },
            timeout=10.0,
        )
        result = resp.json()
        # result["status"], result["data"], result["headers"]
```

### Backend gọi async (send mail)

```python
await client.post(
    "http://agentforge-dispatcher:3010/dispatch/internal",
    headers={
        "x-dispatcher-token": os.environ["DISPATCHER_SECRET"],
        "x-source-service": "backend",
    },
    json={
        "target": "mail",
        "path": "/mail/send",
        "body": {
            "to": user.email,
            "subject": "Xác thực email AgentForge",
            "template": "general",
            "data": {...},
        },
        "source": "backend",
        "event": "user.verification",
        "correlationId": request_id,
    },
)
# Returns immediately: { success: true, messageId: "..." }
# Dispatcher retries up to 3 times before DLQ
```

### TS service gọi stream (code execution)

```ts
const response = await fetch('http://agentforge-dispatcher:3010/dispatch/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-dispatcher-token': process.env.DISPATCHER_SECRET!,
    'x-source-service': 'backend',
  },
  body: JSON.stringify({
    target: 'code-sandbox',
    path: '/execute/stream',
    body: { code: 'print(1)' },
  }),
});

const reader = response.body!.getReader();
// ... pipe to client SSE
```

## Design decisions

| Decision | Reason |
| --- | --- |
| 3 patterns (sync / async / stream) thay vì 1 | Không phải mọi call đều giống nhau — email phải async + retry, AI completion phải stream, auth check phải sync |
| Queue auto-map thay vì client chỉ định | Tránh leak internal topology ra client; client chỉ biết "gửi mail", không cần biết queue |
| TTL+DLX retry thay vì setTimeout | Reliability: setTimeout mất message khi restart |
| Shared secret thay vì mTLS | Đơn giản hơn, đủ cho internal Docker network. mTLS có thể thêm sau |
| Không propagate secret sang target | Target chạy trong cùng network, trust nhau qua `x-source-service`. Nếu cần strong auth, mỗi target tự set secret riêng |
| Single DLQ thay vì per-queue | Đơn giản hoá replay/inspect; message có đủ metadata để biết queue gốc |

## Limitations hiện tại

- **Không có DLQ replay endpoint** — message vào DLQ phải manual xử lý (dự định thêm `POST /dispatch/dlq/replay`).
- **Không có circuit breaker per-target** — target down thì dispatcher vẫn cứ gọi (có retry nhưng không fail-fast).
- **Không có rate limiting per-target** — nếu backend bắn 10k mail/s, dispatcher cứ publish.
- **Không có Prometheus metrics** — chỉ có logs. Production monitoring cần `/metrics` endpoint.
- **Priority `high` không tạo queue riêng** — hiện giữ target queue, chưa map sang queue với concurrency cao hơn.

Những hạn chế này KHÔNG chặn production nếu network nội bộ đáng tin và traffic chưa cao — thêm sau khi có use case cụ thể.

## Related

- [service-mail](../mail/mail-service.md) — consumer chính của async `/internal` dispatch.
- [backend-auth](../../backend/auth.md) — backend gọi mail service qua dispatcher cho verification email.
