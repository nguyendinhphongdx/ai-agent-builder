"""Provider registry — Strategy implementations keyed by canonical name."""
from __future__ import annotations

from app.modules.commerce.payments.checkout.base import PaymentProvider
from app.modules.commerce.payments.checkout.providers.momo import MoMoProvider
from app.modules.commerce.payments.checkout.providers.stripe import StripeProvider

# Single source of truth for the providers this deployment knows about.
# Adding a new gateway means: write the class, drop it in here, done.
_PROVIDERS: dict[str, type[PaymentProvider]] = {
    StripeProvider.name: StripeProvider,
    MoMoProvider.name: MoMoProvider,
}


def get_provider(name: str) -> PaymentProvider:
    """Look up a provider by its canonical id (matches Purchase.provider).

    Raises ValueError on unknown names so callers don't silently route
    to the wrong gateway.
    """
    cls = _PROVIDERS.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown payment provider: {name!r}")
    return cls()


__all__ = ["MoMoProvider", "StripeProvider", "get_provider"]
