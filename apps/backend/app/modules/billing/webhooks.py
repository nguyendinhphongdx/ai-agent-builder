"""Stripe webhook handlers for platform subscriptions.

Routed from the existing ``app/payments/webhooks/stripe.py`` after
signature verification. The marketplace handler already lives there
(checkout.session.completed with metadata.template_id) and we mount
the subscription-flow handlers alongside, dispatched by event type
plus metadata shape.

Events handled here:
  customer.subscription.created    initial provisioning after Checkout
  customer.subscription.updated    plan swap, period roll, cancel
                                   schedule changes
  customer.subscription.deleted    final terminal state — fall back
                                   to free tier
  invoice.payment_failed           flip status → past_due so quota
                                   guards can warn the FE

All handlers are idempotent (re-deliveries are common with Stripe
retries). Returning None for an unrecognised payload is fine —
``stripe_webhook`` returns 200 either way so we don't trigger retries.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_subscription import (
    SUB_STATUS_CANCELED,
    SUB_STATUS_PAST_DUE,
    OrgSubscription,
)
from app.models.organization import Organization
from app.modules.billing import service as billing_service
from app.modules.billing.plans import PLAN_FREE

logger = logging.getLogger("agentforge")


def _ts(unix_seconds: int | None) -> datetime | None:
    if unix_seconds is None:
        return None
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def _find_metered_item(stripe_sub: dict[str, Any]) -> str | None:
    """Walk the subscription's items array, return the id of the
    first sub-item whose price is in metered mode. Stripe puts at
    most one of those per subscription in our setup (Block 2 only
    adds one metered line item).

    Returns None when the plan has no overage line item — that's
    valid for "base fee only" plans.
    """
    items = (stripe_sub.get("items") or {}).get("data") or []
    for item in items:
        price = item.get("price") or {}
        recurring = price.get("recurring") or {}
        if recurring.get("usage_type") == "metered":
            return item.get("id")
    return None


def _org_id_from_metadata(obj: dict[str, Any]) -> uuid.UUID | None:
    meta = obj.get("metadata") or {}
    raw = meta.get("organization_id")
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        logger.warning("billing.webhooks: bad organization_id metadata: %r", raw)
        return None


def _plan_from_metadata(obj: dict[str, Any]) -> str | None:
    return (obj.get("metadata") or {}).get("plan_code")


async def handle_subscription_event(
    db: AsyncSession, stripe_sub: dict[str, Any]
) -> OrgSubscription | None:
    """Handle ``customer.subscription.created`` and
    ``customer.subscription.updated``. Same handler — the diff
    between create and update is just whether the row exists.
    """
    org_id = _org_id_from_metadata(stripe_sub)
    if org_id is None:
        # Could be a pre-existing customer migrated in by hand;
        # try the customer id reverse lookup before giving up.
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
                "billing.webhooks: subscription event without organization_id "
                "metadata or known customer id (sub_id=%s)",
                stripe_sub.get("id"),
            )
            return None

    plan_code = _plan_from_metadata(stripe_sub)
    if not plan_code:
        # Fall back to looking up the recurring line item's nickname
        # — but for our v1 flow Block 2 always sets metadata.plan_code
        # so this path is best-effort recovery.
        items = (stripe_sub.get("items") or {}).get("data") or []
        if items:
            price = items[0].get("price") or {}
            plan_code = price.get("nickname") or price.get("lookup_key")
    if not plan_code:
        logger.warning(
            "billing.webhooks: could not resolve plan_code for sub=%s",
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
        stripe_metered_item_id=_find_metered_item(stripe_sub),
        current_period_start=_ts(stripe_sub.get("current_period_start")),
        current_period_end=_ts(stripe_sub.get("current_period_end")),
        cancel_at_period_end=bool(stripe_sub.get("cancel_at_period_end")),
    )


async def handle_subscription_deleted(
    db: AsyncSession, stripe_sub: dict[str, Any]
) -> OrgSubscription | None:
    """Terminal cancel — flip status + downgrade the org to free.

    Distinct from ``cancel_at_period_end=True`` on an updated event:
    that just schedules; the actual ``deleted`` event fires when the
    period ends and the subscription stops billing.
    """
    sub_id = stripe_sub.get("id")
    if not isinstance(sub_id, str):
        return None
    row = await db.scalar(
        select(OrgSubscription).where(
            OrgSubscription.stripe_subscription_id == sub_id
        )
    )
    if row is None:
        logger.info("billing.webhooks: deleted for unknown sub=%s", sub_id)
        return None

    row.status = SUB_STATUS_CANCELED
    row.cancel_at_period_end = False
    # Drop the org's effective plan back to free. We keep plan_code
    # on the row so analytics can see "they used to be on pro".
    org = await db.get(Organization, row.organization_id)
    if org is not None:
        org.plan = PLAN_FREE
    await db.flush()
    return row


async def handle_invoice_payment_failed(
    db: AsyncSession, invoice: dict[str, Any]
) -> OrgSubscription | None:
    """Mark the subscription as past_due so the FE can surface a
    "payment failed, update your card" banner.

    Quota guards still grant the plan's entitlements while past_due
    — Stripe gives orgs a grace period to fix the card before the
    subscription fully cancels (``customer.subscription.deleted``).
    """
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
