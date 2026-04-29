"""Webhook routers — one per provider.

Each gateway has its own signature scheme (Stripe: HMAC over raw body
via ``stripe.Webhook.construct_event``; MoMo: HMAC over a fixed
param-order string), so a unified endpoint isn't practical. They share
the same shape: verify signature → look up Purchase → dispatch event.
"""
from app.payments.webhooks.momo import router as momo_router
from app.payments.webhooks.stripe import router as stripe_router

__all__ = ["momo_router", "stripe_router"]
