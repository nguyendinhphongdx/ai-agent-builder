---
id: arch-operations
title: Operations - Observability, Payouts, Bootstrap
domain: architecture
tags: [ops, observability, sentry, healthcheck, logging, stripe, connect, payouts, cli]
related: [arch-deployment, arch-system-overview]
summary: Production runbook — JSON access logs, Sentry SDK, /healthz + /readyz, Stripe Connect onboarding, operator CLIs (seed_admin, seed_starter_templates).
---

# Operations Runbook

Everything an operator needs that isn't covered by `docker compose up`.
Pair this with [`deployment.md`](deployment.md) (ports, volumes, compose layout).

---

## 1. First-run bootstrap

Order matters — migrations must succeed before any seed CLI runs.

```bash
# Schema
docker compose exec backend alembic upgrade head

# Root admin (idempotent — promotes if email exists, optionally resets password)
docker compose exec backend python -m app.cli.seed_admin \
    --email admin@example.com --password 'S3cret!'

# 5 starter templates owned by the admin (used by /welcome onboarding wizard)
docker compose exec backend python -m app.cli.seed_starter_templates \
    --owner-email admin@example.com
```

Both seed commands are safe to re-run.

### `seed_admin` flags

| Flag | Behaviour |
|---|---|
| `--email <addr>` | Required. The account to create or promote. |
| `--password <pw>` | Set/replace password. Omit → `$ADMIN_PASSWORD` → interactive prompt. |
| `--name <name>` | Display name when creating. Default `"Root Admin"`. |
| `--promote-only` | If user exists, only update role; leave password untouched. |

### `seed_starter_templates` flags

| Flag | Behaviour |
|---|---|
| `--owner-email <addr>` | Required. Must already be staff (admin/moderator/support). |

Slugs are hard-coded. Re-running upserts metadata + replaces the
`is_current` version's snapshot in place; `fork_count` and rating
aggregates survive the re-seed.

To edit the starter copy itself, change `app/cli/_starter_templates.py`
and re-run the CLI.

---

## 2. Health probes

| Path | Mounted at | Returns |
|---|---|---|
| `GET /healthz` | root | 200 always (process up). Use as `livenessProbe`. |
| `GET /readyz` | root | 200 when Postgres + Redis ping succeed; 503 otherwise. Use as `readinessProbe`. |
| `GET /api/health` | `/api/` | Legacy. Same as `/healthz`. Kept for backward compat. |

`readyz` body example when degraded:

```json
{
  "status": "degraded",
  "checks": {
    "database": "fail: ConnectionRefusedError: ...",
    "redis": "ok"
  }
}
```

Redis is treated as optional — if `REDIS_URL` is unset, the Redis check
short-circuits to `ok` (rate limiting is the only Redis consumer).

---

## 3. Structured logging

Default (`LOG_FORMAT=text`) keeps the old `→ GET /path` / `← GET /path 200 (12ms)`
text logger for dev.

In production set `LOG_FORMAT=json` for one structured line per request:

```json
{
  "ts": "2026-04-29T07:28:28.722Z",
  "level": "INFO",
  "logger": "agentforge.access",
  "msg": "http_request",
  "request_id": "01HW2K…",
  "method": "GET",
  "path": "/api/agents",
  "status": 200,
  "latency_ms": 12,
  "user_id": "a1b2c3d4-…",
  "client": "10.0.1.42"
}
```

- Every response carries `X-Request-ID` (generated if the client didn't
  supply one). Clients can pre-set it to correlate browser logs with
  backend logs.
- Health probes and `/uploads/*` are excluded from the access log to
  keep dashboards clean.
- `JsonFormatter` is also installed on the root handlers, so any
  `logger.warning(...)` call deeper in the stack emits JSON with the
  same `request_id` auto-attached.

Ship to Loki / Datadog / CloudWatch Logs Insights — no parser config
needed.

---

## 4. Error tracking — Sentry

Empty `SENTRY_DSN` keeps the SDK fully dormant (no module-level
breadcrumbs, no network). When set:

```env
SENTRY_DSN=https://abc123@o123456.ingest.sentry.io/789
ENVIRONMENT=production              # or staging | development
RELEASE=$(git rev-parse --short HEAD)  # injected by CI/CD
SENTRY_TRACES_SAMPLE_RATE=0.0       # 0..1; bump when you want perf data
```

Defaults are conservative on purpose:

- `send_default_pii=False` — request bodies, cookies, and headers stay
  local. Tool configs and KB content can carry secrets.
- `traces_sample_rate=0.0` — errors only. Bump deliberately when you
  want performance traces, with sampling tuned to your quota.
- Logging integration: `WARNING` becomes a breadcrumb, `ERROR` becomes
  a captured event.

Frontend Sentry is not yet wired; track in the operations TODO list.

---

## 5. Stripe — Hub V2 paid templates

### 5.1 Buyer-side (Checkout)

```env
STRIPE_SECRET_KEY=sk_live_…
STRIPE_WEBHOOK_SECRET=whsec_…
STRIPE_SUCCESS_URL=https://app.example.com/hub/purchase-complete?session_id={CHECKOUT_SESSION_ID}
STRIPE_CANCEL_URL=https://app.example.com/hub
```

Empty `STRIPE_SECRET_KEY` disables paid templates entirely
(`POST /api/templates/{id}/purchase` returns 503). Stripe's webhook must
target `POST /api/webhooks/stripe` with `STRIPE_WEBHOOK_SECRET` matching
the dashboard's signing secret.

### 5.2 Author payouts (Stripe Connect Express)

```env
STRIPE_PLATFORM_FEE_BPS=1000             # 10% — basis points (1000 = 10.00%)
STRIPE_CONNECT_RETURN_URL=https://app.example.com/settings?onboarded=1
STRIPE_CONNECT_REFRESH_URL=https://app.example.com/settings?refresh=1
```

Onboarding flow:

1. Author clicks **Connect Stripe** in **Settings → Author Payouts**.
2. Backend lazily creates an Express account (`stripe.Account.create`
   with `type=express`) and mints a single-use AccountLink.
3. Frontend opens the URL in a new tab; Stripe collects identity, tax
   forms, bank linking.
4. Stripe fires `account.updated` → backend mirrors `charges_enabled` /
   `payouts_enabled` onto the User row (cached so the publish-paid gate
   doesn't have to round-trip Stripe).
5. Author can now publish paid templates.

### 5.3 Destination charges

When a buyer purchases a paid template:

```python
session = stripe.checkout.Session.create(
    mode="payment",
    payment_intent_data={
        "application_fee_amount": price_cents * STRIPE_PLATFORM_FEE_BPS // 10_000,
        "transfer_data": {"destination": author.stripe_account_id},
    },
    ...
)
```

Stripe collects the buyer's payment, deducts our platform fee, and
routes the rest to the author's connected account. Stripe handles the
payout schedule end-to-end — we don't need a payout cron.

### 5.4 Webhook events we handle

| Event | Handler | Effect |
|---|---|---|
| `checkout.session.completed` | `hub.payment.handle_checkout_completed` | Mark Purchase paid, fork agent, bump fork_count. Idempotent (re-deliveries are no-ops). |
| `account.updated` | `payouts.service.sync_account_from_event` | Mirror `charges_enabled` / `payouts_enabled` onto the User row. |

All other event types are explicitly accepted-and-ignored — return 200
so Stripe doesn't retry.

### 5.5 Disabling Stripe at runtime

To run without Stripe (local dev, free-only deploy):

- Leave `STRIPE_SECRET_KEY` empty.
- Hub publishing still works for free templates.
- `POST /purchase` → 503; `POST /me/payouts/onboarding-link` → 503.
- The webhook endpoint returns 404 (looks genuinely absent).

---

## 6. Operational CLIs — full inventory

```bash
# Run any of these inside the backend container, or locally with the
# backend venv activated. They use the same DATABASE_URL the API uses.

# Promote / create root admin
python -m app.cli.seed_admin --email admin@example.com [--password ...] [--promote-only]

# Refresh the 5 starter templates
python -m app.cli.seed_starter_templates --owner-email admin@example.com

# Migrations (alembic — not under app.cli)
alembic upgrade head
alembic downgrade -1
alembic history
```

Adding a new CLI: drop `apps/backend/app/cli/<name>.py`, expose a
`main()` entrypoint, and document its flags here.

---

## 7. Observability TODOs

Tracked in the operations backlog:

- Frontend Sentry (`@sentry/nextjs` + `instrumentation.ts` + source map
  upload via `withSentryConfig`).
- OpenTelemetry distributed traces (FastAPI → dispatcher → sandbox).
- Per-author payout history page + admin refund flow.
- Author abuse handling (suspend `stripe_charges_enabled` from admin
  panel).
