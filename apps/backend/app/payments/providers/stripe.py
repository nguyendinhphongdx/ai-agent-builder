"""Stripe Checkout — `PaymentProvider` implementation.

Buyer-side flow (mirrored in :class:`MoMoProvider`):
  1. POST /api/templates/{id}/purchase
       └─ create Stripe Checkout Session + Purchase(status=pending) + return URL
  2. Browser redirects to Stripe-hosted checkout page
  3. Buyer pays
  4. Stripe POSTs to /api/webhooks/stripe (handled by `webhooks.stripe`)
       └─ verify signature → mark Purchase paid → fork agent in background
  5. Stripe redirects browser to STRIPE_SUCCESS_URL (FE polls /purchase-status)

Why Checkout Session (not Elements):
  - PCI compliance lives entirely with Stripe.
  - Far less FE plumbing for V2 launch.
  - Trade-off: customer leaves the app briefly. Acceptable for marketplace UX.

Stripe-specific concerns kept here:
  - Connect destination charges (author's `stripe_account_id`).
  - Application fee in basis points (settings.STRIPE_PLATFORM_FEE_BPS).
  - `account.updated` webhook → mirrored to User row (handled in
    `app.payouts.service.sync_account_from_event`, not here).
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, ClassVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.context import current_user_id, reset_current_user_id, set_current_user_id
from app.hub.snapshot import fork_snapshot_into_agent
from app.models.agent import Agent
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.agent_template_version import AgentTemplateVersion
from app.models.user import User
from app.payments.base import PaymentProvider

logger = logging.getLogger("agentforge")


def _stripe():
    """Lazy import — keeps stripe out of the critical path when not configured.

    Exposed at module level (not method) because `app.payouts.service`
    needs the same lazy-imported, api-key-stamped client for Connect
    onboarding flows.
    """
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def is_stripe_configured() -> bool:
    """Module-level alias kept for callers that don't go through the Provider
    abstraction (e.g. webhook router doing its own pre-check)."""
    return StripeProvider.is_configured()


class StripeProvider(PaymentProvider):
    """Stripe Checkout via destination charges (Connect)."""

    name: ClassVar[str] = "stripe"

    @classmethod
    def is_configured(cls) -> bool:
        return bool(settings.STRIPE_SECRET_KEY) and bool(settings.STRIPE_WEBHOOK_SECRET)

    async def create_checkout(
        self, db: AsyncSession, template_id: uuid.UUID
    ) -> tuple[str, AgentTemplatePurchase]:
        if not self.is_configured():
            raise RuntimeError("Paid templates are unavailable — Stripe not configured")

        user_id = current_user_id()
        template = await db.get(AgentTemplate, template_id)
        if template is None or template.status != "published":
            raise ValueError("Template not found or not published")
        if template.price_cents <= 0:
            raise ValueError("Template is free — call /fork instead of /purchase")

        # Author must have onboarded a Connect account before they can be
        # paid. Reject at checkout time rather than letting Stripe accept
        # funds with no path to reroute them.
        author = await db.get(User, template.user_id)
        if author is None:
            raise RuntimeError("Template author missing")
        from app.payouts.service import can_receive_payouts

        if not can_receive_payouts(author):
            raise ValueError(
                "Template is unavailable — the author has not finished setting up payouts"
            )

        # Reuse a paid Purchase if the buyer already owns this template.
        existing_paid = await db.execute(
            select(AgentTemplatePurchase).where(
                AgentTemplatePurchase.buyer_id == user_id,
                AgentTemplatePurchase.template_id == template_id,
                AgentTemplatePurchase.status == "paid",
            ).limit(1)
        )
        if existing_paid.scalar_one_or_none() is not None:
            raise ValueError("You already own this template — fork it from your library")

        version_result = await db.execute(
            select(AgentTemplateVersion).where(
                AgentTemplateVersion.template_id == template_id,
                AgentTemplateVersion.is_current == True,  # noqa: E712
            ).limit(1)
        )
        version = version_result.scalar_one_or_none()
        if version is None:
            raise RuntimeError(f"Template {template_id} has no current version")

        user = await db.get(User, user_id)
        customer_email = user.email if user else None

        platform_fee_cents = (
            template.price_cents * settings.STRIPE_PLATFORM_FEE_BPS
        ) // 10_000

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
            payment_intent_data={
                "application_fee_amount": platform_fee_cents,
                "transfer_data": {"destination": author.stripe_account_id},
            },
            success_url=settings.STRIPE_SUCCESS_URL
            or "https://example.com/?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.STRIPE_CANCEL_URL or "https://example.com/",
            customer_email=customer_email,
            metadata={
                "template_id": str(template_id),
                "version_id": str(version.id),
                "buyer_id": str(user_id),
            },
            idempotency_key=f"purchase:{user_id}:{template_id}:{version.id}",
        )

        purchase = AgentTemplatePurchase(
            buyer_id=user_id,
            template_id=template_id,
            version_id=version.id,
            price_paid_cents=template.price_cents,
            currency=template.currency,
            status="pending",
            provider=self.name,
            provider_transaction_id=session.id,
        )
        db.add(purchase)
        await db.flush()
        await db.refresh(purchase)
        return session.url, purchase

    async def get_purchase_status(
        self, db: AsyncSession, txn_id: str
    ) -> dict[str, Any] | None:
        user_id = current_user_id()
        result = await db.execute(
            select(AgentTemplatePurchase).where(
                AgentTemplatePurchase.provider == self.name,
                AgentTemplatePurchase.provider_transaction_id == txn_id,
                AgentTemplatePurchase.buyer_id == user_id,
            ).limit(1)
        )
        purchase = result.scalar_one_or_none()
        if purchase is None:
            return None

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
            "provider": self.name,
            "template_id": str(purchase.template_id),
            "agent_id": str(agent_id) if agent_id else None,
        }


# ─── Webhook event handler — called by `webhooks.stripe` ──────────────


async def handle_checkout_completed(
    db: AsyncSession, session: dict[str, Any]
) -> Agent | None:
    """Mark the Purchase paid + fork the template (idempotent).

    Returns the new Agent, or None if the Purchase row wasn't found yet
    (Stripe will retry) or this is a duplicate delivery.
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
            AgentTemplatePurchase.provider == "stripe",
            AgentTemplatePurchase.provider_transaction_id == session_id,
        ).limit(1)
    )
    purchase = purchase_result.scalar_one_or_none()
    if purchase is None:
        logger.info(f"stripe webhook: purchase row not found for session {session_id}")
        return None
    if purchase.status == "paid":
        return None

    purchase.status = "paid"
    pi_id = session.get("payment_intent")
    if isinstance(pi_id, str):
        purchase.provider_transaction_id = pi_id
    await db.flush()

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
        reset_current_user_id(token)

    await db.execute(
        update(AgentTemplate)
        .where(AgentTemplate.id == template_id)
        .values(fork_count=AgentTemplate.fork_count + 1)
    )
    await db.flush()

    logger.info(
        f"stripe webhook: forked template={template_id} version={version_id} "
        f"buyer={buyer_id} → agent={agent.id}"
    )
    return agent
