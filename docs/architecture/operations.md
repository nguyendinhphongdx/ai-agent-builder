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

Wired on three runtimes — backend (FastAPI), Next.js server (Node + Edge),
and the browser. Empty DSNs keep each SDK fully dormant; no network, no
module-level side effects.

### 4.1 Backend (`apps/backend`)

```env
SENTRY_DSN=https://abc@o123456.ingest.sentry.io/789
ENVIRONMENT=production              # or staging | development
RELEASE=$(git rev-parse --short HEAD)  # inject from CI/CD
SENTRY_TRACES_SAMPLE_RATE=0.0       # 0..1; bump for perf data
```

Conservative defaults:

- `send_default_pii=False` — request bodies / cookies / headers stay
  local. Tool configs and KB content can carry secrets.
- `traces_sample_rate=0.0` — errors only.
- Logging integration: `WARNING` → breadcrumb, `ERROR` → captured event.

### 4.2 Frontend (`apps/frontend`)

Two SDKs share the project:

- **Server SDK** (`SENTRY_DSN`) — Node + Edge runtimes. Init via
  `src/instrumentation.ts`'s `register()`. Captures Server Component
  crashes, Route Handler errors, middleware exceptions.
- **Browser SDK** (`NEXT_PUBLIC_SENTRY_DSN`) — exposed to the bundle.
  Init via `src/instrumentation-client.ts`. Captures React render errors,
  unhandled rejections, and event-handler throws.

```env
# browser
NEXT_PUBLIC_SENTRY_DSN=
NEXT_PUBLIC_SENTRY_ENVIRONMENT=production
NEXT_PUBLIC_SENTRY_RELEASE=$GIT_SHA
NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=0
# server
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=$GIT_SHA
SENTRY_TRACES_SAMPLE_RATE=0
```

Set the **same DSN** as the backend for unified issue grouping — browser
errors, Next server crashes, and FastAPI exceptions land in the same
project. The backend's `X-Request-ID` response header (see §3) lets you
pivot from a browser issue to the matching backend log line.

Defaults: `tracesSampleRate=0`, `replaysSessionSampleRate=0`,
`replaysOnErrorSampleRate=0`, `sendDefaultPii=false` (matches backend).

### 4.3 Source map upload (CI/CD)

`next.config.ts` is wrapped with `withSentryConfig`. Source maps upload
during `pnpm build` only when these are set in the build environment:

```env
SENTRY_ORG=your-org-slug
SENTRY_PROJECT=your-project-slug
SENTRY_AUTH_TOKEN=sntrys_...   # scope: project:releases
```

Get a token at *Sentry → Settings → Account → API → Auth Tokens*. Without
the token the plugin is a no-op — local builds aren't affected, you just
get minified function names in stack traces.

Source maps are deleted from the client bundle after upload
(`sourcemaps.deleteSourcemapsAfterUpload`) so they don't ship to users.

---

## 5. Buyer-side checkout — multi-provider

`app.payments` is a Strategy + Registry abstraction:

```
app/payments/
  base.py                     ← `PaymentProvider` ABC
  service.py                  ← dispatcher: pick by template.currency
  providers/
    __init__.py               ← registry: {"stripe": StripeProvider, "momo": MoMoProvider}
    stripe.py                 ← StripeProvider + Connect destination charges
    momo.py                   ← MoMoProvider + HMAC IPN verification
  webhooks/
    stripe.py                 ← /api/webhooks/stripe
    momo.py                   ← /api/webhooks/momo
```

The Hub router calls `service.create_checkout_for_template(db, id)` and
gets back `(redirect_url, purchase_row, provider)`. Currency-based
dispatch:

| Template.currency | Provider |
|---|---|
| `VND` | MoMo |
| `USD`, `EUR`, `GBP`, … | Stripe |

Adding a new gateway: write a class that subclasses `PaymentProvider`,
register it in `providers/__init__.py`, extend
`service.get_provider_for_template`. Nothing else above the abstraction
changes.

### 5.1 Stripe — Checkout (buyer side)

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
- `POST /purchase` on USD templates → 503; `POST /me/payouts/onboarding-link` → 503.
- `/api/webhooks/stripe` returns 404 (looks genuinely absent).

### 5.6 MoMo — VND payments (Vietnam)

VND-priced templates route through MoMo. The flow mirrors Stripe Checkout:

```env
MOMO_PARTNER_CODE=        # from MoMo merchant portal
MOMO_ACCESS_KEY=
MOMO_SECRET_KEY=
MOMO_ENDPOINT=https://test-payment.momo.vn   # sandbox
MOMO_RETURN_URL=https://app.example.com/hub/purchase-complete
MOMO_NOTIFY_URL=https://app.example.com/api/webhooks/momo
```

Differences from Stripe:

- **VND only.** `template.currency = "VND"` is required; other currencies
  raise a 400 from `MoMoProvider.create_checkout`. `price_cents` is reused
  as whole-VND amount (column name is a misnomer for VND but the storage
  is identical — a positive integer).
- **No author payouts in V1.** MoMo has no Connect equivalent. Platform
  collects all funds and settles with authors out-of-band. The
  `can_receive_payouts` gate that StripeProvider applies is bypassed for
  VND templates.
- **Signature scheme.** HMAC-SHA256 over a fixed param-order string.
  We sign on outbound `create` requests and verify on inbound IPN.
  Mismatched signatures → 400.

Empty `MOMO_PARTNER_CODE` disables VND checkout (POST /purchase on a
VND template returns 503; `/api/webhooks/momo` returns 404).

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

- OpenTelemetry distributed traces (FastAPI → dispatcher → sandbox).
- Per-author payout history page + admin refund flow.
- Author abuse handling (suspend `stripe_charges_enabled` from admin
  panel).
