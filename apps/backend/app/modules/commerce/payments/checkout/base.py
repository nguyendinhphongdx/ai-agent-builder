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

    from app.models.agent_template_purchase import AgentTemplatePurchase  # noqa: F401


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
    async def is_configured(cls) -> bool:
        """Is the provider enabled with valid secrets?

        Async because the answer comes from ``payment_provider_configs``
        (via :mod:`commerce.payments.config`). Hub router awaits this
        before dispatching so callers see a clean 503.
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

    @abstractmethod
    async def refund(
        self,
        db: "AsyncSession",
        purchase: "AgentTemplatePurchase",
        *,
        reason: str | None = None,
    ) -> None:
        """Issue a refund via the gateway.

        Provider-specific concerns:
        - **Stripe**: `reverse_transfer=True` reverses the Connect
          destination transfer so funds come back from the author's
          account, not the platform's. `refund_application_fee=True`
          gives the platform fee back to the buyer too (full-refund
          semantics — the deal is off).
        - **MoMo**: separate Refund API endpoint with its own HMAC
          signature scheme. Requires the ``transId`` MoMo issued at
          payment time (we store it on the Purchase row from the IPN).

        Caller flips the Purchase row to ``status='refunded'`` and
        commits after this returns. Raises ``RuntimeError`` on gateway
        failure so the admin endpoint can surface a retryable error.
        """

