"""High-level checkout dispatcher used by the Hub router.

The Hub doesn't talk to providers directly — it asks this service to
"create checkout for this template" and gets back a redirect URL. The
provider is picked here based on the template's currency:

    VND  → MoMo
    USD/EUR/GBP/...  → Stripe (default)

When more providers join, extend ``get_provider_for_template``.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.payments.base import PaymentProvider
from app.payments.providers import MoMoProvider, StripeProvider


def get_provider_for_template(template: AgentTemplate) -> PaymentProvider:
    """Pick the canonical buyer-side gateway for a template's currency."""
    if template.currency.upper() == "VND":
        return MoMoProvider()
    return StripeProvider()


async def create_checkout_for_template(
    db: AsyncSession, template_id: uuid.UUID
) -> tuple[str, AgentTemplatePurchase, PaymentProvider]:
    """Resolve provider for the template and mint a checkout session.

    Returns ``(checkout_url, purchase_row, provider)``. The router uses
    ``provider.name`` to populate the response so the FE knows which
    gateway it's redirecting to.
    """
    template = await db.get(AgentTemplate, template_id)
    if template is None:
        raise ValueError("Template not found")
    provider = get_provider_for_template(template)
    url, purchase = await provider.create_checkout(db, template_id)
    return url, purchase, provider


async def get_purchase_status(
    db: AsyncSession, txn_id: str
) -> dict[str, Any] | None:
    """Cross-provider status lookup.

    The FE return-from-checkout page only knows the gateway-issued txn id,
    not which gateway issued it. Try each provider in turn — both lookups
    hit the (provider, provider_transaction_id) compound index, so the
    extra round-trip is one indexed lookup, not a table scan.
    """
    for provider in (StripeProvider(), MoMoProvider()):
        result = await provider.get_purchase_status(db, txn_id)
        if result is not None:
            return result
    return None
