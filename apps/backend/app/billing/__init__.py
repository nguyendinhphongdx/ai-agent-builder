"""Billing module — plans, quotas, Stripe subscriptions, usage reporting.

Distinct from ``app/payments/`` which handles one-time template
purchases via Stripe Connect destination charges. Billing here is
the platform's own SaaS subscription on the *buyer-org's* card.
"""
