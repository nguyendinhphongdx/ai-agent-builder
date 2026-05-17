"""Stripe Subscription provider — recurring billing via Stripe Checkout
+ Billing Portal. Implements :class:`SubscriptionProvider`.

Secrets + price ids come from ``payment_provider_configs`` (Fernet-
encrypted in the DB, cached in-process by
:mod:`commerce.payments.config`). Nothing is read from env here — the
platform admin configures everything via /system/payment-providers.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, ClassVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_subscription import (
    SUB_STATUS_ACTIVE,
    SUB_STATUS_CANCELED,
    SUB_STATUS_PAST_DUE,
    OrgSubscription,
)
from app.models.organization import Organization
from app.models.payment_provider_config import PROVIDER_STRIPE
from app.modules.commerce.payments.config import ProviderConfig, get_provider_config
from app.modules.commerce.payments.subscriptions import service as billing_service
from app.modules.commerce.payments.subscriptions.base import SubscriptionProvider
from app.modules.commerce.payments.subscriptions.plans import PLAN_FREE, Plan
from app.platform.config import settings

logger = logging.getLogger("agentforge")


# Default redirect URLs when the admin hasn't pinned anything in the
# config row. FRONTEND_URL stays in env because it's a platform-wide
# fact, not a payment secret.
def _default_billing_success_url() -> str:
    return (
        f"{settings.FRONTEND_URL}/org/billing?ok=1&session_id={{CHECKOUT_SESSION_ID}}"
    )


def _default_billing_cancel_url() -> str:
    return f"{settings.FRONTEND_URL}/org/billing?cancel=1"


def _default_portal_return_url() -> str:
    return f"{settings.FRONTEND_URL}/org/billing"


def _stripe_with(api_key: str):
    """Configure the Stripe SDK with the per-provider key and return
    the module. Lazy import keeps Stripe out of the import graph when
    no provider is configured (free-tier deployments stay zero-dep)."""
    import stripe

    stripe.api_key = api_key
    return stripe


def _ts(unix_seconds: int | None) -> datetime | None:
    if unix_seconds is None:
        return None
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


class StripeSubscriptionProvider(SubscriptionProvider):
    name: ClassVar[str] = PROVIDER_STRIPE
    display_name: ClassVar[str] = "Stripe (Card)"
    supports_self_serve_signup: ClassVar[bool] = True
    supports_customer_portal: ClassVar[bool] = True

    # ─── Config access ─────────────────────────────────────────

    @classmethod
    async def is_configured(cls) -> bool:
        config = await get_provider_config(cls.name)
        return bool(config and config.is_enabled and config.secret("secret_key"))

    async def _config(self) -> ProviderConfig:
        config = await get_provider_config(self.name)
        if config is None or not config.is_enabled:
            raise RuntimeError("Stripe is not configured")
        if not config.secret("secret_key"):
            raise RuntimeError("Stripe secret_key missing in config")
        return config

    def _resolve_plan_price(self, config: ProviderConfig, plan: Plan) -> tuple[str | None, str | None]:
        """Look up the Stripe price ids for a plan from the config row.

        Config keys follow ``price_<plan_code>`` / ``price_<plan_code>_metered``
        — kept human-readable so the admin can paste from the Stripe
        dashboard URL.
        """
        base = config.config.get(f"price_{plan.code}") or None
        metered = config.config.get(f"price_{plan.code}_metered") or None
        return base, metered

    # ─── Customer bootstrap ────────────────────────────────────

    async def _ensure_customer(
        self,
        db: AsyncSession,
        organization: Organization,
        *,
        config: ProviderConfig,
    ) -> tuple[str, OrgSubscription]:
        sub = await billing_service.get_subscription(db, organization.id)
        if sub is not None and sub.stripe_customer_id:
            return sub.stripe_customer_id, sub

        stripe = _stripe_with(config.secret("secret_key"))
        # metadata.organization_id is the canonical reverse-lookup path
        # for webhooks — never trust email matching.
        customer = stripe.Customer.create(
            email=organization.billing_email or None,
            name=organization.name,
            metadata={"organization_id": str(organization.id)},
            idempotency_key=f"customer-create-org-{organization.id}",
        )

        if sub is None:
            sub = await billing_service.upsert_subscription_from_stripe(
                db,
                organization_id=organization.id,
                plan_code=organization.plan or PLAN_FREE,
                status="none",
                stripe_customer_id=customer.id,
                stripe_subscription_id=None,
            )
        else:
            sub.stripe_customer_id = customer.id
            await db.flush()
        return customer.id, sub

    # ─── SubscriptionProvider implementation ───────────────────

    async def create_checkout(
        self,
        db: AsyncSession,
        *,
        organization: Organization,
        plan: Plan,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> str:
        if plan.code == PLAN_FREE:
            raise ValueError("Cannot checkout the free plan")

        config = await self._config()
        base_price, metered_price = self._resolve_plan_price(config, plan)
        if not base_price:
            raise ValueError(
                f"Plan {plan.code!r} has no Stripe price configured — "
                "add ``price_{plan.code}`` to the Stripe provider config"
            )

        customer_id, _ = await self._ensure_customer(db, organization, config=config)

        stripe = _stripe_with(config.secret("secret_key"))
        line_items: list[dict[str, Any]] = [{"price": base_price, "quantity": 1}]
        if metered_price:
            line_items.append({"price": metered_price})

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=line_items,
            success_url=(
                success_url
                or config.config.get("billing_success_url")
                or _default_billing_success_url()
            ),
            cancel_url=(
                cancel_url
                or config.config.get("billing_cancel_url")
                or _default_billing_cancel_url()
            ),
            subscription_data={
                "metadata": {
                    "organization_id": str(organization.id),
                    "plan_code": plan.code,
                    "provider": self.name,
                },
            },
            idempotency_key=f"sub-checkout-{organization.id}-{plan.code}",
        )
        return session.url

    async def create_portal_session(
        self,
        db: AsyncSession,
        *,
        organization: Organization,
        return_url: str | None = None,
    ) -> str:
        config = await self._config()
        customer_id, _ = await self._ensure_customer(db, organization, config=config)
        stripe = _stripe_with(config.secret("secret_key"))
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=(
                return_url
                or config.config.get("billing_success_url")
                or _default_portal_return_url()
            ),
        )
        return session.url

    async def cancel(
        self,
        db: AsyncSession,
        sub: OrgSubscription,
        *,
        immediate: bool = False,
    ) -> OrgSubscription:
        if not sub.stripe_subscription_id:
            # Manual / comp sub (set_plan backdoor) — flip status only.
            sub.status = SUB_STATUS_CANCELED if immediate else sub.status
            sub.cancel_at_period_end = not immediate
            await db.flush()
            return sub

        config = await self._config()
        stripe = _stripe_with(config.secret("secret_key"))
        if immediate:
            stripe.Subscription.delete(sub.stripe_subscription_id)
            sub.status = SUB_STATUS_CANCELED
            sub.cancel_at_period_end = False
        else:
            stripe.Subscription.modify(
                sub.stripe_subscription_id, cancel_at_period_end=True
            )
            sub.cancel_at_period_end = True
        await db.flush()
        return sub

    # ─── Webhook handling ──────────────────────────────────────
    # Stripe events arrive at the shared Hub receiver
    # (``checkout/webhooks/stripe.py``). The receiver verifies the
    # signature once using the webhook_secret from the provider config,
    # then asks us via :meth:`handles_event` whether this event is
    # ours; if yes it calls :meth:`process_event` with the parsed
    # payload. We don't override ``handle_raw_webhook`` because we
    # don't own a dedicated URL.

    SUBSCRIPTION_EVENT_PREFIXES: ClassVar[tuple[str, ...]] = (
        "customer.subscription.",
        "invoice.paid",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
    )

    @classmethod
    def handles_event(cls, event_type: str) -> bool:
        return any(event_type.startswith(p) for p in cls.SUBSCRIPTION_EVENT_PREFIXES)

    async def process_event(
        self, db: AsyncSession, *, event: dict[str, Any]
    ) -> dict[str, Any]:
        event_type = event.get("type") or ""
        event_id = event.get("id")
        data = (event.get("data") or {}).get("object") or {}

        result = "ignored"
        if event_type in ("customer.subscription.created", "customer.subscription.updated"):
            sub = await self._handle_subscription_event(db, data)
            result = "subscription_upserted" if sub else "subscription_missing_metadata"
        elif event_type == "customer.subscription.deleted":
            sub = await self._handle_subscription_deleted(db, data)
            result = "subscription_canceled" if sub else "unknown_subscription"
        elif event_type == "invoice.payment_failed":
            sub = await self._handle_invoice_payment_failed(db, data)
            result = "marked_past_due" if sub else "unknown_subscription"
        elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
            sub = await self._handle_invoice_paid(db, data)
            result = "marked_active" if sub else "unknown_subscription"

        return {
            "provider": self.name,
            "event_id": event_id,
            "type": event_type,
            "result": result,
        }

    # ─── Webhook handlers (Stripe-specific event shapes) ───────

    def _find_metered_item(self, stripe_sub: dict[str, Any]) -> str | None:
        items = (stripe_sub.get("items") or {}).get("data") or []
        for item in items:
            price = item.get("price") or {}
            recurring = price.get("recurring") or {}
            if recurring.get("usage_type") == "metered":
                return item.get("id")
        return None

    def _org_id_from_metadata(self, obj: dict[str, Any]) -> uuid.UUID | None:
        meta = obj.get("metadata") or {}
        raw = meta.get("organization_id")
        if not raw:
            return None
        try:
            return uuid.UUID(raw)
        except ValueError:
            logger.warning("stripe.webhook: bad organization_id metadata: %r", raw)
            return None

    async def _handle_subscription_event(
        self, db: AsyncSession, stripe_sub: dict[str, Any]
    ) -> OrgSubscription | None:
        org_id = self._org_id_from_metadata(stripe_sub)
        if org_id is None:
            customer_id = stripe_sub.get("customer")
            if isinstance(customer_id, str):
                row = await db.scalar(
                    select(OrgSubscription).where(
                        OrgSubscription.stripe_customer_id == customer_id
                    )
                )
                if row is not None:
                    org_id = row.organization_id
            if org_id is None:
                logger.warning(
                    "stripe.webhook: subscription event without organization_id "
                    "metadata or known customer id (sub_id=%s)",
                    stripe_sub.get("id"),
                )
                return None

        plan_code = (stripe_sub.get("metadata") or {}).get("plan_code")
        if not plan_code:
            items = (stripe_sub.get("items") or {}).get("data") or []
            if items:
                price = items[0].get("price") or {}
                plan_code = price.get("nickname") or price.get("lookup_key")
        if not plan_code:
            logger.warning(
                "stripe.webhook: could not resolve plan_code for sub=%s",
                stripe_sub.get("id"),
            )
            return None

        return await billing_service.upsert_subscription_from_stripe(
            db,
            organization_id=org_id,
            plan_code=plan_code,
            status=stripe_sub.get("status") or "active",
            stripe_customer_id=stripe_sub.get("customer"),
            stripe_subscription_id=stripe_sub.get("id"),
            stripe_metered_item_id=self._find_metered_item(stripe_sub),
            current_period_start=_ts(stripe_sub.get("current_period_start")),
            current_period_end=_ts(stripe_sub.get("current_period_end")),
            cancel_at_period_end=bool(stripe_sub.get("cancel_at_period_end")),
        )

    async def _handle_subscription_deleted(
        self, db: AsyncSession, stripe_sub: dict[str, Any]
    ) -> OrgSubscription | None:
        sub_id = stripe_sub.get("id")
        if not isinstance(sub_id, str):
            return None
        row = await db.scalar(
            select(OrgSubscription).where(
                OrgSubscription.stripe_subscription_id == sub_id
            )
        )
        if row is None:
            return None
        row.status = SUB_STATUS_CANCELED
        row.cancel_at_period_end = False
        org = await db.get(Organization, row.organization_id)
        if org is not None:
            org.plan = PLAN_FREE
        await db.flush()
        return row

    async def _handle_invoice_payment_failed(
        self, db: AsyncSession, invoice: dict[str, Any]
    ) -> OrgSubscription | None:
        sub_id = invoice.get("subscription")
        if not isinstance(sub_id, str):
            return None
        row = await db.scalar(
            select(OrgSubscription).where(
                OrgSubscription.stripe_subscription_id == sub_id
            )
        )
        if row is None:
            return None
        row.status = SUB_STATUS_PAST_DUE
        await db.flush()
        return row

    async def _handle_invoice_paid(
        self, db: AsyncSession, invoice: dict[str, Any]
    ) -> OrgSubscription | None:
        sub_id = invoice.get("subscription")
        if not isinstance(sub_id, str):
            return None
        row = await db.scalar(
            select(OrgSubscription).where(
                OrgSubscription.stripe_subscription_id == sub_id
            )
        )
        if row is None:
            return None
        if row.status == SUB_STATUS_PAST_DUE:
            row.status = SUB_STATUS_ACTIVE
        # Refresh period window from the invoice's base line item.
        lines = (invoice.get("lines") or {}).get("data") or []
        for line in lines:
            price = line.get("price") or {}
            recurring = price.get("recurring") or {}
            if recurring.get("usage_type") == "metered":
                continue
            period = line.get("period") or {}
            start = _ts(period.get("start"))
            end = _ts(period.get("end"))
            if start is not None:
                row.current_period_start = start
            if end is not None:
                row.current_period_end = end
            break
        await db.flush()
        return row


# ─── Public utilities for the Hub Stripe webhook receiver ───────────
#
# The shared receiver needs the secret_key + webhook_secret for the
# Stripe SDK upfront, before any provider dispatch. Exposing these
# small helpers keeps the receiver from importing the provider's
# internals.


async def get_stripe_secret_key() -> str | None:
    config = await get_provider_config(PROVIDER_STRIPE)
    if config is None or not config.is_enabled:
        return None
    return config.secret("secret_key") or None


async def get_stripe_webhook_secret() -> str | None:
    config = await get_provider_config(PROVIDER_STRIPE)
    if config is None or not config.is_enabled:
        return None
    return config.secret("webhook_secret") or None
