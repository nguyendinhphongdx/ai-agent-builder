"""Stripe Subscription provider — recurring billing via Stripe Checkout
+ Billing Portal. Implements :class:`SubscriptionProvider`.

This is the canonical implementation; logic was previously inlined in
``stripe_client.py`` (kept as a thin re-export shim during the
abstraction migration).
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
from app.modules.commerce.payments.subscriptions import service as billing_service
from app.modules.commerce.payments.subscriptions.base import SubscriptionProvider
from app.modules.commerce.payments.subscriptions.plans import PLAN_FREE, Plan
from app.platform.config import settings

logger = logging.getLogger("agentforge")


def _stripe():
    """Lazy import — keeps Stripe out of the import graph when not
    configured. Free-tier-only deployments stay zero-dep."""
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _ts(unix_seconds: int | None) -> datetime | None:
    if unix_seconds is None:
        return None
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


class StripeSubscriptionProvider(SubscriptionProvider):
    name: ClassVar[str] = "stripe"
    display_name: ClassVar[str] = "Stripe (Card)"
    supports_self_serve_signup: ClassVar[bool] = True
    supports_customer_portal: ClassVar[bool] = True

    @classmethod
    def is_configured(cls) -> bool:
        # Webhook secret could be missing on a brand-new deploy that
        # hasn't wired Stripe yet — but Checkout itself needs only the
        # secret key. ``handle_webhook_event`` raises if the webhook
        # secret is missing at that codepath.
        return bool(settings.STRIPE_SECRET_KEY)

    # ─── Customer bootstrap ────────────────────────────────────

    async def _ensure_customer(
        self, db: AsyncSession, organization: Organization
    ) -> tuple[str, OrgSubscription]:
        """Resolve or create the Stripe Customer for ``organization``."""
        sub = await billing_service.get_subscription(db, organization.id)
        if sub is not None and sub.stripe_customer_id:
            return sub.stripe_customer_id, sub

        stripe = _stripe()
        # ``metadata.organization_id`` is the canonical reverse-lookup
        # path for webhooks — never trust email matching.
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
        if not self.is_configured():
            raise RuntimeError("Stripe is not configured")
        base_price = plan.stripe_price_id()
        if not base_price:
            raise ValueError(
                f"Plan {plan.code!r} has no Stripe price configured — "
                "set the corresponding STRIPE_PRICE_* env var"
            )
        if plan.code == PLAN_FREE:
            raise ValueError("Cannot checkout the free plan")

        customer_id, _ = await self._ensure_customer(db, organization)

        stripe = _stripe()
        line_items: list[dict[str, Any]] = [{"price": base_price, "quantity": 1}]
        metered_price = plan.stripe_metered_price_id()
        if metered_price:
            # Metered overage line item — quantity starts at 0 on
            # Checkout for usage_type=metered; usage records arrive
            # via the reporter loop.
            line_items.append({"price": metered_price})

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=line_items,
            success_url=(
                success_url
                or settings.STRIPE_BILLING_SUCCESS_URL
                or f"{settings.FRONTEND_URL}/org/billing?ok=1&session_id={{CHECKOUT_SESSION_ID}}"
            ),
            cancel_url=(
                cancel_url
                or settings.STRIPE_BILLING_CANCEL_URL
                or f"{settings.FRONTEND_URL}/org/billing?cancel=1"
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
        if not self.is_configured():
            raise RuntimeError("Stripe is not configured")
        customer_id, _ = await self._ensure_customer(db, organization)
        stripe = _stripe()
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=(
                return_url
                or settings.STRIPE_BILLING_SUCCESS_URL
                or f"{settings.FRONTEND_URL}/org/billing"
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
            # Manual / comp sub (set_plan backdoor) — just flip status.
            sub.status = SUB_STATUS_CANCELED if immediate else sub.status
            sub.cancel_at_period_end = not immediate
            await db.flush()
            return sub

        stripe = _stripe()
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
    #
    # Stripe events arrive at the shared Hub receiver
    # (``checkout/webhooks/stripe.py``). The receiver verifies the
    # signature once, then asks us via :meth:`handles_event` whether
    # this event is ours; if yes it calls :meth:`process_event` with
    # the parsed payload. We don't override ``handle_raw_webhook``
    # because we don't own a dedicated URL.

    SUBSCRIPTION_EVENT_PREFIXES: ClassVar[tuple[str, ...]] = (
        "customer.subscription.",
        "invoice.paid",
        "invoice.payment_succeeded",
        "invoice.payment_failed",
    )

    @classmethod
    def handles_event(cls, event_type: str) -> bool:
        """Whether the shared Stripe webhook router should route this
        event type to our :meth:`process_event` instead of the Hub
        checkout handler."""
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
