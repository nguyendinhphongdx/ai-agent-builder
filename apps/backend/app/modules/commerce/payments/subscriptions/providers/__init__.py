"""Subscription provider registry.

Single source of truth for the recurring-billing gateways this
deployment knows about. Adding one means: write the class, drop it
in here, done.

Lookup pattern is intentional — every caller goes through
``get_provider(name)`` or ``self_serve_providers()`` so we never
have a free-floating ``StripeSubscriptionProvider()`` instantiation
that bypasses the configured check.
"""
from __future__ import annotations

from app.modules.commerce.payments.subscriptions.base import SubscriptionProvider
from app.modules.commerce.payments.subscriptions.providers.stripe import (
    StripeSubscriptionProvider,
)

_PROVIDERS: dict[str, type[SubscriptionProvider]] = {
    StripeSubscriptionProvider.name: StripeSubscriptionProvider,
    # MoMo / VNPay aren't here yet — recurring with those gateways
    # requires special partnerships and a separate codepath (token
    # tap → backend charge). Add them when the deal closes.
}


def get_provider(name: str) -> SubscriptionProvider:
    """Look up a provider by canonical name. Raises ValueError on
    unknown so misconfigured callers fail loudly."""
    cls = _PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown subscription provider: {name!r}")
    return cls()


def configured_providers() -> list[SubscriptionProvider]:
    """Every registered provider whose env / DB secrets are present.
    Used by ``/api/billing/providers`` so the FE picker can render
    one button per active gateway."""
    return [cls() for cls in _PROVIDERS.values() if cls.is_configured()]


def default_provider() -> SubscriptionProvider | None:
    """First configured provider. Used as the auto-pick when the
    legacy single-provider flow (``POST /api/billing/checkout``
    without explicit provider) is invoked.

    Returns None when nothing is configured — caller maps to 503.
    """
    for cls in _PROVIDERS.values():
        if cls.is_configured():
            return cls()
    return None


__all__ = [
    "StripeSubscriptionProvider",
    "configured_providers",
    "default_provider",
    "get_provider",
]
