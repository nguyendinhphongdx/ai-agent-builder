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


async def configured_providers() -> list[SubscriptionProvider]:
    """Every registered provider with an enabled DB row + valid
    secrets. Used by ``/api/billing/providers`` so the FE picker can
    render one button per active gateway.

    Async because ``is_configured`` reads the cached
    ``payment_provider_configs`` row (TTL 30s, so the hot path is
    in-memory after first read)."""
    out: list[SubscriptionProvider] = []
    for cls in _PROVIDERS.values():
        if await cls.is_configured():
            out.append(cls())
    return out


async def default_provider() -> SubscriptionProvider | None:
    """First enabled provider — auto-pick for the single-provider
    checkout flow. None when nothing is configured (caller → 503)."""
    for cls in _PROVIDERS.values():
        if await cls.is_configured():
            return cls()
    return None


__all__ = [
    "StripeSubscriptionProvider",
    "configured_providers",
    "default_provider",
    "get_provider",
]
