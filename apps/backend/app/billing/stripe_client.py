"""Stripe client — Checkout + Customer + Billing Portal for platform subs.

Separate from ``app.payments.providers.stripe`` (marketplace template
purchases via Connect destination charges). This module covers the
*platform-billing* flow: orgs paying us for the SaaS itself.

Lazy imports stripe so the module is free to load when no Stripe key
is configured (free-tier-only deployments stay zero-dep).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import service as billing_service
from app.billing.plans import Plan, get_plan
from app.config import settings
from app.models.organization import Organization

logger = logging.getLogger("agentforge")


def is_configured() -> bool:
    """Block 2 needs only the secret key — webhooks ship in Block 4."""
    return bool(settings.STRIPE_SECRET_KEY)


def _stripe():
    """Lazy import — keeps stripe out of the import graph for callers
    that never touch billing (free-tier servers, tests, CLI tools).
    """
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


async def ensure_customer(
    db: AsyncSession, organization: Organization
) -> tuple[str, "OrgSubscription"]:  # noqa: F821
    """Resolve a Stripe Customer id for the org, creating one if needed.

    Subscription row is upserted so we have somewhere to stash the
    customer id even before a plan is picked. Returning the row lets
    the caller mutate it in the same transaction.
    """
    if not is_configured():
        raise RuntimeError("Stripe is not configured — set STRIPE_SECRET_KEY")

    sub = await billing_service.get_subscription(db, organization.id)
    if sub is not None and sub.stripe_customer_id:
        return sub.stripe_customer_id, sub

    stripe = _stripe()
    # ``metadata.organization_id`` is the canonical reverse lookup
    # path for webhooks — we never trust raw email or name matching.
    customer = stripe.Customer.create(
        email=organization.billing_email or None,
        name=organization.name,
        metadata={"organization_id": str(organization.id)},
        idempotency_key=f"customer-create-org-{organization.id}",
    )

    if sub is None:
        # Stamp a row so the customer id has a home. plan_code starts
        # as the legacy column value (or free) until checkout lands.
        sub = await billing_service.upsert_subscription_from_stripe(
            db,
            organization_id=organization.id,
            plan_code=organization.plan or "free",
            status="none",
            stripe_customer_id=customer.id,
            stripe_subscription_id=None,
        )
    else:
        sub.stripe_customer_id = customer.id
        await db.flush()

    return customer.id, sub


async def create_checkout_session(
    db: AsyncSession,
    *,
    organization: Organization,
    plan: Plan,
    success_url: str | None = None,
    cancel_url: str | None = None,
) -> str:
    """Hosted Checkout for switching the org to ``plan``.

    Returns the redirect URL. The actual subscription state lands via
    the ``customer.subscription.created`` webhook (Block 4); our
    redirect lands the user on the billing dashboard which polls for
    the new state.
    """
    if not is_configured():
        raise RuntimeError("Stripe is not configured")
    base_price = plan.stripe_price_id()
    if not base_price:
        raise ValueError(
            f"Plan {plan.code!r} has no configured Stripe price — "
            "set the corresponding STRIPE_PRICE_* env var"
        )

    customer_id, _ = await ensure_customer(db, organization)

    stripe = _stripe()
    line_items: list[dict[str, Any]] = [{"price": base_price, "quantity": 1}]
    # Metered overage line item — quantity defaults to 0 on Checkout
    # for "usage_type=metered" prices, Stripe records arrive via the
    # reporter (Block 3).
    metered_price = plan.stripe_metered_price_id()
    if metered_price:
        line_items.append({"price": metered_price})

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        line_items=line_items,
        success_url=(
            success_url
            or settings.STRIPE_BILLING_SUCCESS_URL
            or f"{settings.FRONTEND_URL}/settings/billing?ok=1&session_id={{CHECKOUT_SESSION_ID}}"
        ),
        cancel_url=(
            cancel_url
            or settings.STRIPE_BILLING_CANCEL_URL
            or f"{settings.FRONTEND_URL}/settings/billing?cancel=1"
        ),
        subscription_data={
            "metadata": {
                "organization_id": str(organization.id),
                "plan_code": plan.code,
            },
        },
        # Idempotent across the same plan upgrade attempt within the
        # same 24h window. Means refreshing the upgrade page reuses
        # the existing session instead of churning new Stripe ids.
        idempotency_key=f"sub-checkout-{organization.id}-{plan.code}",
    )
    return session.url


async def create_portal_session(
    db: AsyncSession,
    *,
    organization: Organization,
    return_url: str | None = None,
) -> str:
    """Stripe Billing Portal — Stripe-hosted UI for managing the
    subscription (cancel, swap card, view invoices, change plan via
    plan-update flow).

    Reduces our own self-serve surface — we don't need /cancel,
    /update-card, /invoices routes; the portal covers all of it and
    is PCI-compliance-bundled.
    """
    if not is_configured():
        raise RuntimeError("Stripe is not configured")

    customer_id, _ = await ensure_customer(db, organization)
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url
        or settings.STRIPE_BILLING_SUCCESS_URL
        or f"{settings.FRONTEND_URL}/settings/billing",
    )
    return session.url
