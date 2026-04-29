"""Stripe Checkout integration for paid templates.

Flow:
  1. POST /templates/{id}/purchase
       └─ create Stripe Checkout Session + Purchase(status=pending) + return URL
  2. Browser redirects to Stripe-hosted checkout page
  3. Buyer pays
  4. Stripe POSTs to /api/webhooks/stripe (handled in :mod:`hub.webhook_router`)
       └─ verify signature → mark Purchase paid → fork agent in background
  5. Stripe redirects browser to STRIPE_SUCCESS_URL (FE polls /purchase-status)

Why Checkout Session (not Elements):
  - PCI compliance lives entirely with Stripe.
  - Far less FE plumbing for V2 launch.
  - Trade-off: customer leaves the app briefly. Acceptable for marketplace UX.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_user_id
from app.hub.snapshot import fork_snapshot_into_agent
from app.models.agent import Agent
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.agent_template_version import AgentTemplateVersion
from app.models.user import User

logger = logging.getLogger("agentforge")


def is_stripe_configured() -> bool:
    """Cheap pre-check used by routers to short-circuit with a 503."""
    return bool(settings.STRIPE_SECRET_KEY) and bool(settings.STRIPE_WEBHOOK_SECRET)


def _stripe():
    """Lazy import — keeps stripe out of the critical path when not configured."""
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


# ─── Create checkout session ──────────────────────────────────────────


async def create_checkout_session(
    db: AsyncSession, template_id: uuid.UUID
) -> tuple[str, AgentTemplatePurchase]:
    """Create a Stripe Checkout Session for the current user buying ``template_id``.

    Returns ``(checkout_url, purchase_row)``. Caller commits the DB and
    redirects the browser to ``checkout_url``.

    Raises:
        ValueError — template not found / not published / not paid / already purchased
        RuntimeError — Stripe not configured (caller maps to 503)
    """
    if not is_stripe_configured():
        raise RuntimeError("Paid templates are unavailable — Stripe not configured")

    user_id = current_user_id()

    template = await db.get(AgentTemplate, template_id)
    if template is None or template.status != "published":
        raise ValueError("Template not found or not published")
    if template.price_cents <= 0:
        raise ValueError("Template is free — call /fork instead of /purchase")

    # Reuse a paid Purchase if the buyer already owns this template (free reinstall).
    existing_paid = await db.execute(
        select(AgentTemplatePurchase).where(
            AgentTemplatePurchase.buyer_id == user_id,
            AgentTemplatePurchase.template_id == template_id,
            AgentTemplatePurchase.status == "paid",
        ).limit(1)
    )
    if existing_paid.scalar_one_or_none() is not None:
        raise ValueError("You already own this template — fork it from your library")

    # Pick the current version to lock in.
    version_result = await db.execute(
        select(AgentTemplateVersion).where(
            AgentTemplateVersion.template_id == template_id,
            AgentTemplateVersion.is_current == True,  # noqa: E712
        ).limit(1)
    )
    version = version_result.scalar_one_or_none()
    if version is None:
        raise RuntimeError(f"Template {template_id} has no current version")

    # Email is optional but reduces friction — Stripe pre-fills it.
    user = await db.get(User, user_id)
    customer_email = user.email if user else None

    stripe = _stripe()
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": template.currency.lower(),
                    "product_data": {
                        "name": template.title[:200],
                        "description": (template.description or "")[:500] or None,
                    },
                    "unit_amount": template.price_cents,
                },
                "quantity": 1,
            }
        ],
        success_url=settings.STRIPE_SUCCESS_URL or "https://example.com/?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=settings.STRIPE_CANCEL_URL or "https://example.com/",
        customer_email=customer_email,
        # ``metadata`` is what we read in the webhook to find the Purchase row.
        # Keep it small and exact — Stripe also surfaces it in the dashboard.
        metadata={
            "template_id": str(template_id),
            "version_id": str(version.id),
            "buyer_id": str(user_id),
        },
        # Idempotency key prevents duplicate sessions if the FE retries the
        # POST. Scoped per (buyer, template) — refunds + re-buy use a new key
        # implicitly via a fresh purchase row id.
        idempotency_key=f"purchase:{user_id}:{template_id}:{version.id}",
    )

    purchase = AgentTemplatePurchase(
        buyer_id=user_id,
        template_id=template_id,
        version_id=version.id,
        price_paid_cents=template.price_cents,
        currency=template.currency,
        status="pending",
        stripe_payment_intent_id=session.id,  # session id; PI id arrives via webhook
    )
    db.add(purchase)
    await db.flush()
    await db.refresh(purchase)

    return session.url, purchase


# ─── Webhook handling ─────────────────────────────────────────────────


async def handle_checkout_completed(
    db: AsyncSession, session: dict[str, Any]
) -> Agent | None:
    """Mark the Purchase paid and fork the template into the buyer's library.

    Idempotent: a re-delivery of the same Stripe event is a no-op (the
    Purchase row is already paid + the agent already exists).

    Returns the new Agent, or None if the Purchase row was not found
    (e.g. webhook fired before the create_checkout_session DB commit landed —
    Stripe will retry).
    """
    session_id = session.get("id")
    if not session_id:
        logger.warning("stripe webhook: missing session id")
        return None

    metadata = session.get("metadata") or {}
    template_id_raw = metadata.get("template_id")
    version_id_raw = metadata.get("version_id")
    buyer_id_raw = metadata.get("buyer_id")
    if not (template_id_raw and version_id_raw and buyer_id_raw):
        logger.warning(f"stripe webhook missing metadata: {metadata}")
        return None

    purchase_result = await db.execute(
        select(AgentTemplatePurchase).where(
            AgentTemplatePurchase.stripe_payment_intent_id == session_id
        ).limit(1)
    )
    purchase = purchase_result.scalar_one_or_none()
    if purchase is None:
        # Purchase row hasn't landed yet — Stripe will retry.
        logger.info(f"stripe webhook: purchase row not found for session {session_id}")
        return None

    if purchase.status == "paid":
        # Already processed (this is a Stripe retry).
        return None

    purchase.status = "paid"
    # Replace the session id with the actual PaymentIntent id so we can
    # look up the charge for refunds later.
    pi_id = session.get("payment_intent")
    if isinstance(pi_id, str):
        purchase.stripe_payment_intent_id = pi_id
    await db.flush()

    # Fork the template into the buyer's library. We can't use
    # current_user_id() here because webhooks don't run in a request
    # scope — set the contextvar manually for the duration of this call.
    from app.context import set_current_user_id

    template_id = uuid.UUID(template_id_raw)
    version_id = uuid.UUID(version_id_raw)
    buyer_id = uuid.UUID(buyer_id_raw)

    token = set_current_user_id(buyer_id)
    try:
        version = await db.get(AgentTemplateVersion, version_id)
        if version is None:
            logger.error(f"stripe webhook: version {version_id} disappeared")
            return None

        agent = await fork_snapshot_into_agent(
            db, version.snapshot, template_id=template_id, version_id=version_id
        )
    finally:
        from app.context import reset_current_user_id

        reset_current_user_id(token)

    # Bump fork count on the parent template
    from sqlalchemy import update

    await db.execute(
        update(AgentTemplate)
        .where(AgentTemplate.id == template_id)
        .values(fork_count=AgentTemplate.fork_count + 1)
    )
    await db.flush()

    logger.info(
        f"stripe webhook: forked template={template_id} "
        f"version={version_id} buyer={buyer_id} → agent={agent.id}"
    )
    return agent


# ─── Status polling ───────────────────────────────────────────────────


async def get_purchase_status(
    db: AsyncSession, session_id: str
) -> dict[str, Any] | None:
    """Return current status of a checkout session for the FE poller.

    Scoped to current_user — buyers can only see their own purchase status.
    """
    user_id = current_user_id()
    result = await db.execute(
        select(AgentTemplatePurchase).where(
            AgentTemplatePurchase.stripe_payment_intent_id == session_id,
            AgentTemplatePurchase.buyer_id == user_id,
        ).limit(1)
    )
    purchase = result.scalar_one_or_none()
    if purchase is None:
        return None

    # Find the agent forked from this purchase, if any. We don't store a
    # direct FK from Purchase → Agent, so look it up by template + buyer +
    # created_after_purchase. Cheap because both columns are indexed.
    agent_id: uuid.UUID | None = None
    if purchase.status == "paid":
        agent_result = await db.execute(
            select(Agent.id).where(
                Agent.user_id == user_id,
                Agent.template_id == purchase.template_id,
                Agent.template_version_id == purchase.version_id,
            ).order_by(Agent.created_at.desc()).limit(1)
        )
        agent_id = agent_result.scalar_one_or_none()

    return {
        "status": purchase.status,
        "template_id": str(purchase.template_id),
        "agent_id": str(agent_id) if agent_id else None,
    }
