---
id: flows-subscription-billing
title: Subscription Signup & Billing Flow
domain: flows
tags: [billing, subscriptions, stripe, plans, quota, webhooks]
related: [frontend-feature-billing, api-billing-endpoints, backend-module-commerce-payments]
summary: End-to-end flow from picking a paid plan, completing Stripe Checkout, receiving webhook confirmation, and ongoing lifecycle (renewals, plan swap, cancel, dunning).
---

# Subscription Signup & Billing Flow

## Overview

An organization upgrades from `free` to a paid plan (`starter` / `pro` / `enterprise`) via Stripe-hosted Checkout. Stripe handles all card data; our backend only stores the linkage (`stripe_customer_id`, `stripe_subscription_id`) plus the canonical `OrgSubscription` row. State changes (renew, swap card, cancel) flow back through signed webhooks.

Distinct from the **Hub template purchase** flow (one-time, Connect destination charges — see `hub-payment.md`). This doc covers the **platform subscription**: orgs paying us for the SaaS itself.

## Actors

| Actor | Role |
|---|---|
| **Customer org admin** | Holds `billing.manage` permission. The only role that can pick a plan or open the portal. |
| **Stripe** | PCI scope owner. Hosts Checkout, hosts the customer portal, sources all webhooks. |
| **AgentForge backend** | Mints Checkout sessions, receives webhooks, mirrors `OrgSubscription` table, enforces quota at runtime. |
| **AgentForge frontend** | Plan picker UI + status dashboard. Never sees card data. |

## Plan catalogue

Plans are **declarative in code** ([`commerce/payments/subscriptions/plans.py`](../../apps/backend/app/modules/commerce/payments/subscriptions/plans.py)). Changing a tier = code deploy, not an admin form — keeps quotas type-safe and version-controlled.

| Plan | Tokens/mo | KB queries/mo | Workspaces | Members | Stripe price env |
|---|---|---|---|---|---|
| `free` | 100K | 1K | 1 | 3 | — (not for sale) |
| `starter` | 1M | 10K | 3 | 10 | `STRIPE_PRICE_STARTER` |
| `pro` | 10M | 100K | unlimited | 50 | `STRIPE_PRICE_PRO` |
| `enterprise` | unlimited | unlimited | unlimited | unlimited | `STRIPE_PRICE_ENTERPRISE` (sales-led) |

Each tier may also carry a `STRIPE_PRICE_*_METERED` for token-overage billing (usage_type=metered Stripe price).

Self-serve filtering: a plan is visible in `/api/billing/plans` only when its `stripe_price_setting` resolves to a non-empty env value. Enterprise stays hidden until a sales deal is closed and a private Stripe price is minted.

## Step-by-Step

### 1. Discover plans

Frontend [`BillingView`](../../apps/frontend/src/features/billing/views/BillingView.tsx) at `/org/billing` loads:

```
GET /api/billing/plans          → list of self-serve plans
GET /api/billing/subscription   → current plan + quota usage
```

The plans payload powers the picker; the subscription payload powers the "You are on **Pro**" card with progress bars (tokens used / KB queries used vs limit).

### 2. Pick a plan → mint Checkout session

User clicks "Switch to Pro":

```
POST /api/billing/checkout
{
  "plan_code": "pro",
  "success_url": "https://app.example.com/org/billing?ok=1",
  "cancel_url":  "https://app.example.com/org/billing?cancel=1"
}
```

Backend ([`stripe_client.create_checkout_session`](../../apps/backend/app/modules/commerce/payments/subscriptions/stripe_client.py)):

1. Validate plan: must exist, must NOT be `free`, must have `stripe_price_id()`.
2. **Resolve / create Stripe Customer** via `ensure_customer()`:
   - First call → `stripe.Customer.create(email=org.billing_email, metadata={organization_id})` with `idempotency_key=customer-create-org-{org_id}`.
   - Upsert a placeholder `OrgSubscription` row carrying the customer id (status=`none`).
3. **Create Checkout Session** (`mode=subscription`):
   - `line_items=[{price: STRIPE_PRICE_PRO}]` + optional metered line.
   - `subscription_data.metadata={organization_id, plan_code}` — used by the webhook for reverse lookup.
   - `success_url` / `cancel_url` — caller override or `STRIPE_BILLING_*_URL` env fallback.
   - `idempotency_key=sub-checkout-{org_id}-{plan_code}` — refreshing the upgrade page reuses the same session within Stripe's 24h window.
4. Return `{ url }` → frontend does `window.location.href = url`.

The user is now on Stripe's hosted page.

### 3. User pays on Stripe-hosted Checkout

Card data lives entirely in Stripe's iframe — backend never sees it. Outcomes:

- **Success** → Stripe redirects browser to `success_url` with `?session_id={CHECKOUT_SESSION_ID}`. The frontend lands on the billing dashboard which polls `GET /api/billing/subscription` until `status` flips to `active`.
- **Cancel / back** → redirects to `cancel_url`. No subscription created.

The page redirect is asynchronous to the webhook — the user may land on the success page **before** our DB has the subscription row. The polling loop covers this race.

### 4. Webhook: provisioning

Stripe fires **`customer.subscription.created`** seconds later to `POST /api/webhooks/stripe`.

Webhook router ([`commerce/payments/checkout/webhooks/stripe.py`](../../apps/backend/app/modules/commerce/payments/checkout/webhooks/stripe.py)):

1. Verify HMAC via `stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)`. Bad signature → 400 (no retry).
2. Dispatch by event type. Subscription events route to [`subscriptions/webhooks.handle_subscription_event`](../../apps/backend/app/modules/commerce/payments/subscriptions/webhooks.py).

`handle_subscription_event`:

1. **Resolve `organization_id`**:
   - Primary: `subscription.metadata.organization_id` (set in step 2).
   - Fallback: reverse-lookup `OrgSubscription` row by `stripe_customer_id` — covers customers migrated by hand.
2. **Resolve `plan_code`**:
   - Primary: `subscription.metadata.plan_code` (set in step 2).
   - Fallback: parse line item `nickname` / `lookup_key`.
3. **Upsert `OrgSubscription`** via `billing_service.upsert_subscription_from_stripe`:
   - Stash `status`, `stripe_subscription_id`, period boundaries, metered item id, `cancel_at_period_end`.
   - **Mirror** `plan_code` onto `organizations.plan` so legacy quota checks reading the column stay correct.

Idempotent — Stripe retries (network blips, our 5xx) re-apply the same state.

### 5. Frontend confirms

The billing dashboard polls `/api/billing/subscription`:

```json
{
  "subscription": {
    "plan":   { "code": "pro", "name": "Pro", ... },
    "status": "active",
    "current_period_start": "2026-05-17T...",
    "current_period_end":   "2026-06-17T...",
    "cancel_at_period_end": false,
    "has_stripe_subscription": true
  },
  "tokens":     { "used": 234567, "limit": 10000000, "pct": 2.3 },
  "kb_queries": { "used": 421,    "limit": 100000,   "pct": 0.4 }
}
```

The picker now shows `current` next to Pro. Quota progress bars render off `tokens` / `kb_queries`. Done.

## Ongoing lifecycle

### Renewal (automatic)

Each period end Stripe issues a new invoice + charges the saved card. On success:

- `invoice.paid` → `handle_invoice_paid`:
  - Clears `past_due` → `active` (if it was past_due).
  - **Rolls `current_period_start/end`** from the invoice's recurring line item (Stripe updates the invoice object before the subscription object — reading here is one event sooner).

User sees no change. Quota counters reset on the new period boundary.

### Plan swap / cancel via Customer Portal

User clicks "Manage billing" in `/org/billing`:

```
POST /api/billing/portal
{ "return_url": "https://app.example.com/org/billing" }
```

Backend mints a [Stripe Billing Portal](https://stripe.com/docs/billing/subscriptions/customer-portal) session, returns URL. The portal is Stripe-hosted and covers:

- Cancel subscription
- Swap card / update billing email
- Download invoices
- Change plan (Stripe-hosted plan-update flow)

We **don't build** `/cancel`, `/update-card`, `/invoices` routes — the portal owns them all.

Portal actions land back as webhooks:

| Portal action | Stripe event | Handler effect |
|---|---|---|
| Plan change | `customer.subscription.updated` | `handle_subscription_event` re-applies new plan + metered item |
| Schedule cancel | `customer.subscription.updated` (with `cancel_at_period_end=true`) | Mirrors the flag; access kept until period end |
| Restart canceled | `customer.subscription.updated` | Flips `cancel_at_period_end=false` |
| Final cancel at period end | `customer.subscription.deleted` | `handle_subscription_deleted`: status=`canceled`, **drop `organizations.plan` back to `free`** |

`plan_code` on the row is kept after cancel so analytics can see "they used to be on pro".

### Payment failure (dunning)

Card declined on renewal:

- `invoice.payment_failed` → `handle_invoice_payment_failed`:
  - Flip `OrgSubscription.status` → `past_due`.
  - **Quota guards still grant full entitlements** while past_due (grace period — Stripe retries the charge several times before giving up).
- Frontend surfaces a banner: "Payment failed, update your card" (link → portal).
- User updates card via portal → Stripe retries → `invoice.paid` fires → `handle_invoice_paid` flips back to `active`.
- All Stripe retries fail → `customer.subscription.deleted` → forced downgrade to `free`.

### Admin override (system org)

The platform owner can bypass Stripe entirely for comps, enterprise deals signed offline, or internal staff orgs:

```
POST /api/system/subscriptions/{org_id}/set-plan
{ "plan_code": "enterprise" }
```

`subs_service.set_plan` → `billing.set_plan` → `upsert_subscription_from_stripe(..., status="active", stripe_*=None)`. Mirrors `organizations.plan` so quota guards see the upgraded tier. Gated by `require_platform_admin` (must be owner/admin of the system org).

Cancel similarly:
```
POST /api/system/subscriptions/{org_id}/cancel
{ "immediate": false }   # default: cancel at period end
```

## Quota enforcement

Runtime guards live in [`subscriptions/quota.py`](../../apps/backend/app/modules/commerce/payments/subscriptions/quota.py). Two scopes:

- **Org pool** (the plan's `monthly_llm_tokens` / `monthly_kb_queries`) — summed across every workspace in the org over the current period.
- **Workspace soft cap** (`workspaces.monthly_token_quota_override`) — bounds a single workspace inside the shared org pool. Hard block regardless of metered overage; exists to prevent waste, not enable extra billing.

Check order on every billable op:

```
workspace cap → fail → QuotaExceeded (HTTP 402)
org cap      → metered plan? bill overage and continue
              → non-metered? QuotaExceeded (HTTP 402)
```

`QuotaExceeded.detail` is structured so the FE can render a plan-specific upgrade prompt without a second round-trip:

```json
{
  "code":  "quota_exceeded",
  "kind":  "tokens" | "kb_queries",
  "used":  10500000,
  "limit": 10000000,
  "plan":  "pro"
}
```

Callers wire at cheap-to-fail boundaries: chat SSE checks before the stream starts, retriever checks before the SQL hit.

### Period boundaries

| Subscription state | Period |
|---|---|
| Live Stripe sub (`active` / `trialing` / `past_due`) | `current_period_start/end` from Stripe |
| No sub or `canceled` | Rolling 30 days from now |

### Metered overage (token overage billing)

Tiers with `STRIPE_PRICE_*_METERED` set have a metered line item appended to the Checkout session. The usage reporter (`billing.usage_reporter` background loop) ships incremental token counts to Stripe via `subscription_item.usage_records` once per period:

1. Cursor-based scan over `usage_events` table.
2. Aggregate by `OrgSubscription.stripe_metered_item_id`.
3. POST to Stripe.
4. Save `last_reported_event_id` + `last_reported_event_created_at` as the next cursor.

Reporter currently `disabled` when Stripe isn't configured — log shows `INFO billing.usage_reporter: disabled (Stripe not configured)` at boot.

## State machine

```
              ┌────────┐
              │  none  │  Free tier (no Stripe object)
              └───┬────┘
                  │ Checkout success →
                  │ customer.subscription.created webhook
                  ▼
              ┌────────┐
       ┌──────│ active │──────┐
       │      └───┬────┘      │
       │          │           │ Card decline →
       │ Schedule │           │ invoice.payment_failed
       │ cancel   │           ▼
       │ (portal) │       ┌────────┐
       │          │       │past_due│  (full entitlements kept,
       │          │       └───┬────┘   grace period)
       │          │           │
       │          │           │ Card fixed → invoice.paid
       │          │           └────► active
       │          │
       │          │ Period end with cancel_at_period_end →
       │          │ customer.subscription.deleted
       │          ▼
       │      ┌──────────┐
       │      │ canceled │  organizations.plan ← 'free'
       │      └──────────┘
       │
       │ Plan swap → customer.subscription.updated
       └────► active (new plan)
```

## Failure modes

| Failure | Detection | Recovery |
|---|---|---|
| Stripe webhook signature fails | `construct_event` raises | 400 returned; Stripe retries (won't help — bad shared secret = ops fix) |
| Org has no `billing.manage` permission | `require_active_permission` | 403 — checkout endpoint refuses |
| Plan not self-serve (no `STRIPE_PRICE_*`) | `plan.is_self_serve()` check | 400 `plan_not_self_serve` |
| Stripe Customer created twice | `idempotency_key=customer-create-org-{id}` | Stripe returns same customer; no duplicate row |
| Webhook arrives before our DB commit lands | `_org_id_from_metadata` fallback to customer reverse lookup | Found via `stripe_customer_id`; if still missing, Stripe retries |
| Subscription row missing on webhook | logger.warning + return None | 200 returned, no retry — manual intervention via system admin |
| Card declined on renewal | `invoice.payment_failed` | `past_due` status, grace period, retry by Stripe |
| All retries fail | `customer.subscription.deleted` | Forced downgrade to free; quota dropping immediately |
| Past_due banner stuck after card fix | `invoice.paid` flips back to active | One event sooner than `subscription.updated` |

## Configuration

Required env vars to enable subscriptions ([`.env.example`](../../apps/backend/.env.example)):

```bash
STRIPE_SECRET_KEY=sk_live_...           # required (any env)
STRIPE_WEBHOOK_SECRET=whsec_...         # required (signed webhook verification)

STRIPE_PRICE_STARTER=price_...          # at least one needed for self-serve
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ENTERPRISE=price_...       # sales-led — keep empty to hide

STRIPE_PRICE_STARTER_METERED=price_...  # optional, for token-overage tiers
STRIPE_PRICE_PRO_METERED=price_...

STRIPE_BILLING_SUCCESS_URL=https://app.example.com/org/billing?ok=1
STRIPE_BILLING_CANCEL_URL=https://app.example.com/org/billing?cancel=1
```

Empty `STRIPE_SECRET_KEY` → `/api/billing/checkout` returns 503 `billing_unavailable`, FE renders a "billing is disabled on this deployment" message.

## Local dev with Stripe CLI

```bash
# 1. Install Stripe CLI: brew install stripe/stripe-cli/stripe
# 2. Login: stripe login
# 3. Forward webhooks:
stripe listen --forward-to localhost:8000/api/webhooks/stripe
# → prints whsec_xxx — paste as STRIPE_WEBHOOK_SECRET into .env

# 4. Test a checkout flow:
stripe trigger checkout.session.completed
stripe trigger customer.subscription.created

# 5. Use test card 4242 4242 4242 4242 on the Checkout page.
```

## See also

- [`hub-payment.md`](./hub-payment.md) — marketplace template purchase (one-time, Connect destination)
- [`backend-module-commerce-payments.md`](../backend/commerce-payments.md) — module structure
- [`api-billing-endpoints.md`](../api/billing.md) — endpoint reference
- [Stripe Checkout docs](https://stripe.com/docs/payments/checkout)
- [Stripe Customer Portal docs](https://stripe.com/docs/billing/subscriptions/customer-portal)
