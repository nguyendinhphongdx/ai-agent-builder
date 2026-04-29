"""Buyer-side checkout — multi-provider abstraction.

Strategy pattern: one ``PaymentProvider`` subclass per gateway (Stripe,
MoMo, …). The Hub router calls into ``service.create_checkout_for_template``
which picks the right provider based on the template's currency.

Author payouts (Stripe Connect) live in ``app.payouts`` — that's an
author-side onboarding concern, separate from the buyer-side checkout
strategy here.
"""
from app.payments.base import PaymentProvider
from app.payments.service import (
    create_checkout_for_template,
    get_provider_for_template,
    get_purchase_status,
)

__all__ = [
    "PaymentProvider",
    "create_checkout_for_template",
    "get_provider_for_template",
    "get_purchase_status",
]
