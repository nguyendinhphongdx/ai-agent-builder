"""Abstract Strategy interface for buyer-side checkout providers.

Each gateway (Stripe, MoMo, …) implements this contract. New providers
add a class + register in ``providers/__init__.py``; nothing else above
needs to know about them.

Webhook signature schemes vary widely (Stripe: HMAC over raw body via
``stripe.Webhook.construct_event``; MoMo: HMAC over a fixed param-order
string), so each provider also exposes its own webhook router. The
abstract interface here only covers the request-time path that the Hub
router talks to.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.agent_template_purchase import AgentTemplatePurchase


class PaymentProvider(ABC):
    """One implementation per payment gateway.

    Subclasses declare ``name`` (used as the discriminator in
    ``agent_template_purchases.provider``) and override the three async
    methods. Stateless — instances carry no per-request data; safe to
    instantiate ad-hoc inside ``service.get_provider_for_template``.
    """

    name: ClassVar[str]
    """Canonical id, matches the value stored on Purchase rows."""

    @classmethod
    @abstractmethod
    def is_configured(cls) -> bool:
        """Cheap pre-check: does this deployment have the secrets to use it?

        Hub router uses this to short-circuit with 503 instead of erroring
        deeper in the stack.
        """

    @abstractmethod
    async def create_checkout(
        self, db: "AsyncSession", template_id: uuid.UUID
    ) -> tuple[str, "AgentTemplatePurchase"]:
        """Mint a checkout session for the current user.

        Returns ``(redirect_url, purchase_row)``. Caller commits the DB
        and redirects the browser to ``redirect_url``. The Purchase row
        is in ``status='pending'``; the provider's webhook flips it to
        ``'paid'`` once payment completes.

        Raises:
            ValueError: bad input (template missing/free/already-bought).
            RuntimeError: provider not configured / upstream API failure.
        """

    @abstractmethod
    async def get_purchase_status(
        self, db: "AsyncSession", txn_id: str
    ) -> dict[str, Any] | None:
        """Return current Purchase status, scoped to ``current_user_id``.

        Body shape: ``{status, provider, template_id, agent_id?}``.
        Returns ``None`` when the txn id doesn't match any of the user's
        Purchases (caller maps to 404).
        """
