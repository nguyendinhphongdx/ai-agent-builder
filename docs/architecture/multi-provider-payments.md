---
id: arch-multi-provider-payments
title: Multi-Provider Payment Architecture
domain: architecture
tags: [payments, providers, stripe, momo, vnpay, sepay, subscriptions, hub, abstraction, strategy-pattern]
related: [flows-subscription-billing, backend-module-commerce-payments]
summary: Strategy-pattern abstraction over payment providers (Stripe, MoMo, …) for two distinct flows — one-time Hub template purchases (PaymentProvider) and recurring org subscriptions (SubscriptionProvider). Each gateway implements the appropriate interface, registers in a per-flow registry, and the router talks to the abstraction. Covers contract design, registry lookup, webhook dispatch (shared-URL vs dedicated-URL), provider capability flags, and step-by-step "add a new provider" cookbook.
---

# Multi-Provider Payment Architecture

## Why an abstraction at all

AgentForge accepts money in two structurally different ways:

| Flow | Cardinality | Contract | Examples |
|---|---|---|---|
| **Hub template purchase** | One-time | `Purchase` row → fork agent | Stripe (USD card), MoMo (VND wallet) |
| **Org subscription** | Recurring | `OrgSubscription` row → plan grants entitlements | Stripe (Card/SEPA/…), future: VNPay token, Sepay invoice |

Both need: hosted checkout, signed webhook, refund / cancel / portal. **What** the gateway does is uniform — **how** wildly different (signature schemes, currency support, recurring model, KYC flow).

Without the abstraction, the Hub router branches on `if provider == "stripe": ... elif provider == "momo": ...`, the subscription router branches similarly, every new provider touches 5 files. With it: write one class, drop it in the registry, done.

## Two interface hierarchies, not one

```
PaymentProvider             SubscriptionProvider
(one-time / Hub)            (recurring / org-billing)
  ├─ StripeProvider           ├─ StripeSubscriptionProvider
  └─ MoMoProvider              └─ (future) VNPayProvider, SepayProvider
```

They look similar but the **lifecycles diverge**: `PaymentProvider.refund()` makes no sense for a recurring sub (you cancel + close period instead), `SubscriptionProvider.create_portal_session()` makes no sense for a one-time purchase (no recurring state to manage).

Splitting also matches the **VN reality**: MoMo / VNPay one-time works the same as Stripe; their *recurring* offerings are different beasts (separate merchant agreements, some don't even support autopay — Sepay = "auto-detect bank transfer" not autopay). Keeping interfaces separate lets a VN gateway ship one-time without pretending to support a recurring API it doesn't have.

## `PaymentProvider` — one-time Hub flow

```python
# app/modules/commerce/payments/checkout/base.py
class PaymentProvider(ABC):
    name: ClassVar[str]           # canonical id stored on Purchase.provider

    @classmethod
    @abstractmethod
    def is_configured(cls) -> bool: ...

    @abstractmethod
    async def create_checkout(
        self, db, template_id: uuid.UUID
    ) -> tuple[str, AgentTemplatePurchase]: ...   # → (redirect_url, pending Purchase)

    @abstractmethod
    async def get_purchase_status(
        self, db, txn_id: str
    ) -> dict | None: ...   # → {status, provider, template_id, agent_id?}

    @abstractmethod
    async def refund(
        self, db, purchase, *, reason: str | None = None
    ) -> None: ...
```

Stateless — instantiate ad-hoc inside `service.get_provider_for_template`. Each provider also owns a webhook router (`checkout/webhooks/{stripe,momo}.py`) because signature schemes don't share.

Current implementations:

| Provider | File | Notes |
|---|---|---|
| `StripeProvider` (name=`stripe`) | `checkout/providers/stripe.py` | Connect destination charge → author payout direct; webhook signature via `stripe.Webhook.construct_event` |
| `MoMoProvider` (name=`momo`) | `checkout/providers/momo.py` | HMAC over fixed param-order string; per-author merchant via `users.momo_*_enc` |

Registry: `checkout/providers/__init__.py` exposes `get_provider(name)` keyed on `Purchase.provider`.

## `SubscriptionProvider` — recurring billing

```python
# app/modules/commerce/payments/subscriptions/base.py
class SubscriptionProvider(ABC):
    name: ClassVar[str]           # canonical id stored on OrgSubscription.provider
    display_name: ClassVar[str]   # UI label
    supports_self_serve_signup: ClassVar[bool] = True
    supports_customer_portal:   ClassVar[bool] = True

    @classmethod
    @abstractmethod
    def is_configured(cls) -> bool: ...

    @abstractmethod
    async def create_checkout(
        self, db, *, organization, plan, success_url=None, cancel_url=None
    ) -> str: ...

    @abstractmethod
    async def create_portal_session(
        self, db, *, organization, return_url=None
    ) -> str: ...

    @abstractmethod
    async def cancel(
        self, db, sub, *, immediate: bool = False
    ) -> OrgSubscription: ...

    # Webhook
    @abstractmethod
    async def process_event(
        self, db, *, event: dict
    ) -> dict: ...   # verified-event dispatch (shared-URL providers)

    async def handle_raw_webhook(
        self, db, *, signature, raw_body
    ) -> dict:
        """Self-verify signature, parse, delegate. Default raises —
        only providers with a dedicated URL override (MoMo, VNPay)."""
        raise NotImplementedError
```

### Capability flags

`supports_self_serve_signup` / `supports_customer_portal` let the FE pick the right UX without sniffing the provider name:

```python
provider = sub_providers.default_provider()
if not provider.supports_customer_portal:
    # render "Contact support to change plan" instead of "Manage billing"
    ...
```

VNPay (when added) sets `supports_customer_portal=False` — VNPay has no hosted portal; we'd surface a custom in-app cancel flow.

### Two webhook strategies

| Strategy | When to use | Override |
|---|---|---|
| **`process_event`** (verified event in) | Provider shares a webhook URL with another flow (Stripe: Hub checkout + Connect onboarding + subscriptions all on `/api/webhooks/stripe`) | Required |
| **`handle_raw_webhook`** (raw body + sig) | Provider has dedicated URL with own signature scheme (MoMo / VNPay) | Override; keeps default `process_event` minimal |

The shared Stripe receiver verifies the signature once and dispatches by event-type prefix:

```python
# checkout/webhooks/stripe.py
if StripeSubscriptionProvider.handles_event(event_type):
    await StripeSubscriptionProvider().process_event(db, event=event)
elif event_type == "checkout.session.completed":
    await handle_checkout_completed(db, obj)
elif event_type == "account.updated":
    await sync_account_from_event(db, obj)
```

Each `SubscriptionProvider` declares `handles_event(event_type) -> bool` so the dispatcher doesn't need to know the provider's internal taxonomy.

## Registry pattern

```python
# subscriptions/providers/__init__.py
_PROVIDERS: dict[str, type[SubscriptionProvider]] = {
    StripeSubscriptionProvider.name: StripeSubscriptionProvider,
}

def get_provider(name: str) -> SubscriptionProvider: ...
def configured_providers() -> list[SubscriptionProvider]: ...
def default_provider() -> SubscriptionProvider | None: ...
```

Three accessors — one for explicit name lookup (webhook dispatch), one for "give me everything the FE picker can show" (filtered by `is_configured`), one for "the legacy single-provider flow" (auto-pick first configured).

Adding a new provider:

1. Write `subscriptions/providers/myprovider.py` subclassing `SubscriptionProvider`.
2. Add to `_PROVIDERS` dict in `__init__.py`.
3. Done. Router + webhook receiver + FE picker pick it up automatically.

## Flow comparison: Stripe vs MoMo vs VNPay

| Concern | Stripe Subscription | MoMo Subscription | VNPay Token |
|---|---|---|---|
| Hosted checkout | Stripe Checkout (full-page redirect) | No native — would need custom card-token flow | Token issuance API → custom UI |
| Customer portal | Stripe Billing Portal (cancel, swap card, plan change) | None | None |
| Webhook URL | Shared `/api/webhooks/stripe` | Dedicated `/api/webhooks/momo` | Dedicated `/api/webhooks/vnpay` |
| Webhook sig | HMAC via SDK (`construct_event`) | HMAC over param-order string | HMAC-SHA512 of query params |
| Recurring model | Native (`subscription` mode) | Special partnership required, not self-serve | Token re-charge via API call |
| Currency | USD/EUR/SGD/… | VND only | VND only |
| Refund | API + `reverse_transfer` for Connect | Separate Refund API + HMAC | Refund API |
| Capability flags | `self_serve=True, portal=True` | `self_serve=False, portal=False` | `self_serve=True, portal=False` |

**Pragmatic rollout for AgentForge**: Stripe for international + tech-savvy VN devs with int'l cards; **Sepay** (auto-confirm bank transfer) is the first VN provider to add because it doesn't need any merchant approval — just a bank account + Sepay subscription.

## Cookbook — add a new subscription provider

### 1. Implement the class

```python
# subscriptions/providers/sepay.py
from app.modules.commerce.payments.subscriptions.base import SubscriptionProvider

class SepaySubscriptionProvider(SubscriptionProvider):
    name = "sepay"
    display_name = "Bank transfer (Sepay)"
    supports_self_serve_signup = True
    supports_customer_portal = False    # no Sepay-hosted portal

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.SEPAY_API_KEY)

    async def create_checkout(self, db, *, organization, plan, success_url=None, cancel_url=None) -> str:
        # 1. Allocate invoice id, save pending OrgSubscription row
        # 2. Generate VietQR with memo = "AGENTFORGE-{org_id}-{invoice_id}"
        # 3. Return our own /pay-confirm/{invoice_id} page URL
        ...

    async def create_portal_session(self, db, *, organization, return_url=None) -> str:
        raise RuntimeError("Sepay does not provide a hosted customer portal")

    async def cancel(self, db, sub, *, immediate: bool = False) -> OrgSubscription:
        # Sepay isn't autopay — cancellation = "stop sending future invoices".
        # Mark the row + cron job won't re-issue for the next period.
        ...

    async def process_event(self, db, *, event: dict) -> dict:
        # Not used — Sepay has its own URL
        return {"provider": self.name, "result": "noop"}

    async def handle_raw_webhook(self, db, *, signature, raw_body) -> dict:
        # 1. Verify HMAC over raw_body using SEPAY_HMAC_SECRET
        # 2. Parse: extract invoice id from memo
        # 3. Mark OrgSubscription paid + roll period
        ...
```

### 2. Register

```python
# subscriptions/providers/__init__.py
_PROVIDERS = {
    StripeSubscriptionProvider.name: StripeSubscriptionProvider,
    SepaySubscriptionProvider.name: SepaySubscriptionProvider,
}
```

### 3. Mount the dedicated webhook (only if `handle_raw_webhook` overridden)

```python
# app/modules/api/webhooks_sepay.py
@router.post("/webhooks/sepay")
async def sepay_webhook(request: Request, x_sepay_signature: str | None = Header(None)):
    body = await request.body()
    async with async_session_factory() as db:
        try:
            await SepaySubscriptionProvider().handle_raw_webhook(
                db, signature=x_sepay_signature, raw_body=body
            )
            await db.commit()
        except ValueError as exc:
            raise HTTPException(400, str(exc))
```

Mount in `main.py` alongside the Stripe + MoMo receivers.

### 4. Add env

```bash
# .env.example
SEPAY_API_KEY=
SEPAY_HMAC_SECRET=
SEPAY_BANK_ACCOUNT_ID=
```

### 5. Surface in FE picker

`/api/billing/providers` (forthcoming) returns `configured_providers()`. FE renders one button per provider. No FE code change needed when adding a new one — server-driven discovery.

### 6. Smoke test

```python
# test_sepay_provider.py
async def test_create_checkout_emits_vietqr(db_session):
    provider = SepaySubscriptionProvider()
    url = await provider.create_checkout(db_session, organization=org, plan=plan)
    assert "/pay-confirm/" in url

async def test_webhook_marks_paid(db_session):
    body = b'{"invoice_id":"...","amount":..."}'
    sig = compute_test_sig(body)
    audit = await SepaySubscriptionProvider().handle_raw_webhook(
        db_session, signature=sig, raw_body=body
    )
    assert audit["result"] == "subscription_paid"
```

## Provider configuration in DB (future)

Currently provider secrets live in env (`STRIPE_SECRET_KEY`, `MOMO_*`, `SEPAY_*`). For platform-admin UX — non-dev product owner toggles providers from `/system/payment-providers` without touching env — see the design proposal in **payment-providers-admin.md** (next phase).

TL;DR: introduce `payment_providers` table with Fernet-encrypted secrets, registry reads DB-first with env fallback, admin UI to enable/test/edit per provider. No interface changes — providers stay the same classes.

## Idempotency + dedup

| Concern | Mechanism |
|---|---|
| Stripe webhook re-delivery | `stripe_webhook_events(event_id PK)` table — `INSERT … ON CONFLICT DO NOTHING` inside handler txn |
| Stripe Checkout retry from FE | `idempotency_key=sub-checkout-{org}-{plan}` — Stripe dedupes within 24h |
| Stripe Customer creation race | `idempotency_key=customer-create-org-{org}` |
| Process-event double-fire | Each handler upsert-style — safe to re-run |
| MoMo / VNPay webhook re-delivery | Per-provider dedup table (each provider owns its own — schemas differ) |

## Refactor history

Pre-refactor: `subscriptions/stripe_client.py` had all Stripe logic inline + `subscriptions/webhooks.py` had module-level handler functions. Hub webhook receiver imported subscription handlers by name and dispatched per event type.

Post-refactor (current):
- Logic moved to `subscriptions/providers/stripe.py` implementing `SubscriptionProvider`.
- `subscriptions/webhooks.py` deleted.
- `subscriptions/stripe_client.py` deleted (background reporter imports `_stripe` directly from the provider module — the only Stripe-direct caller left).
- Hub receiver dispatches by `StripeSubscriptionProvider.handles_event(...)` → `provider.process_event(...)`.

Cleaner separation: subscription concerns live entirely under `subscriptions/`, Hub receiver only knows "Stripe sub provider exists, ask it whether this event is its".

## See also

- [`flows-subscription-billing`](../flows/subscription-billing.md) — end-to-end signup → checkout → webhook → renewal walkthrough
- [`backend-module-commerce-payments`](../backend/commerce-payments.md) — module layout
- [Stripe API events catalogue](https://stripe.com/docs/api/events/types)
