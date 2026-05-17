"""Abstract Strategy interface for subscription (recurring) providers.

Mirrors :mod:`app.modules.commerce.payments.checkout.base` but for the
platform-billing flow (orgs pay us monthly) instead of one-time
template purchases.

Why a separate hierarchy from ``checkout.PaymentProvider``:

  * **Contract shape differs.** One-time checkout returns a
    ``Purchase`` row + redirect; subscription checkout returns a
    redirect that ends at a ``customer.subscription.created`` webhook
    + an ``OrgSubscription`` row.

  * **Lifecycle differs.** Subscription has billing portal, period
    rolls, dunning, scheduled cancel. One-time has refund + done.

  * **VN provider gap.** MoMo / VNPay one-time work the same as
    Stripe; their *recurring* offerings are very different — most
    require a separate merchant agreement, some don't expose
    autopay at all (Sepay = "auto-detect bank transfer" not
    autopay). Keeping the interfaces separate lets the registry
    publish ``StripeSubscriptionProvider`` while the VN providers
    only ship one-time on ``checkout.PaymentProvider``.

New subscription provider: subclass + register in
``providers/__init__.py``. Nothing else needs to know.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.organization import Organization
    from app.models.org_subscription import OrgSubscription
    from app.modules.commerce.payments.subscriptions.plans import Plan


class SubscriptionProvider(ABC):
    """One implementation per recurring-billing gateway.

    Subclasses declare ``name`` (matches ``OrgSubscription.provider``
    once that column lands) and override the lifecycle methods.
    Stateless — instantiate ad-hoc inside the service layer.
    """

    name: ClassVar[str]
    """Canonical id, matches the value stored on OrgSubscription rows."""

    display_name: ClassVar[str]
    """Human-readable label for the admin UI / picker."""

    supports_self_serve_signup: ClassVar[bool] = True
    """False for providers that need sales-led onboarding (eg. enterprise
    invoice-only). UI hides them from the per-plan picker."""

    supports_customer_portal: ClassVar[bool] = True
    """False for providers without a hosted self-serve management page
    (eg. VNPay). UI hides the "Manage billing" button and surfaces a
    "Contact support to change plan" message instead."""

    @classmethod
    @abstractmethod
    async def is_configured(cls) -> bool:
        """Is the provider enabled with valid secrets in the DB?

        Async because the answer comes from ``payment_provider_configs``
        (via the cached :mod:`commerce.payments.config` service). Router
        awaits this before delegating, so callers see a clean 503
        instead of an upstream API error from missing keys.
        """

    @abstractmethod
    async def create_checkout(
        self,
        db: "AsyncSession",
        *,
        organization: "Organization",
        plan: "Plan",
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> str:
        """Mint a hosted-checkout URL for switching ``organization`` to
        ``plan``. Returns the redirect URL.

        The actual ``OrgSubscription`` row lands via the provider's
        webhook (see ``handle_webhook``); the FE polls the subscription
        endpoint after redirect until ``status='active'``.

        Raises:
            ValueError: bad input (plan not for sale on this provider,
                plan=free, etc.).
            RuntimeError: provider not configured / upstream API failure.
        """

    @abstractmethod
    async def create_portal_session(
        self,
        db: "AsyncSession",
        *,
        organization: "Organization",
        return_url: str | None = None,
    ) -> str:
        """Mint a hosted customer-management URL. Used for cancel,
        swap card, view invoices, change plan.

        Raises ``RuntimeError`` if ``supports_customer_portal`` is False
        — caller should check that flag first.
        """

    @abstractmethod
    async def cancel(
        self,
        db: "AsyncSession",
        sub: "OrgSubscription",
        *,
        immediate: bool = False,
    ) -> "OrgSubscription":
        """Cancel a live subscription.

        ``immediate=False`` (default) → schedule cancel at period end,
        keep entitlements until then. ``immediate=True`` → terminate
        now (use for fraud / ToS violation only).

        Idempotent — calling cancel on an already-canceled sub returns
        the row unchanged.
        """

    # ─── Webhook surface ───────────────────────────────────────
    #
    # Stripe shares one webhook URL with the Hub checkout flow, so
    # signatures are verified once in the central Stripe receiver and
    # dispatched to ``process_event`` by event-type prefix. MoMo /
    # VNPay have provider-specific URLs (separate signature schemes)
    # and override ``handle_raw_webhook`` for self-verification.

    @abstractmethod
    async def process_event(
        self, db: "AsyncSession", *, event: dict[str, Any]
    ) -> dict[str, Any]:
        """Mutate ``OrgSubscription`` for one already-verified provider
        event. Returns audit dict ``{provider, event_id, type, result}``.
        Idempotent — re-delivery returns the same shape with
        ``result='ignored'`` when state is already where it should be.
        """

    async def handle_raw_webhook(
        self,
        db: "AsyncSession",
        *,
        signature: str | None,
        raw_body: bytes,
    ) -> dict[str, Any]:
        """Verify the provider's signature over ``raw_body``, parse the
        payload, delegate to :meth:`process_event`.

        Default raises ``NotImplementedError`` — only providers with a
        dedicated webhook URL (MoMo, VNPay) override this. Stripe's
        events arrive through the shared Hub receiver which calls
        :meth:`process_event` directly after verifying once.
        """
        raise NotImplementedError(
            f"{type(self).__name__} doesn't own a dedicated webhook URL"
        )
