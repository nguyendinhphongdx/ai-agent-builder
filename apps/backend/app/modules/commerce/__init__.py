"""commerce/ — money flow.

  * payments/subscriptions/  recurring Stripe subscriptions (plans + quota)
  * payments/checkout/       one-time purchases (hub agent buys, Stripe + MoMo)
  * payments/payouts/        outflows to hub authors (marketplace revshare)
  * usage/                   metered usage events (read API for dashboard,
                              fed by ``background/billing_reporter`` to Stripe)
  * hub/                     marketplace (listings, reviews, snapshots)

Everything in here touches money — currency, taxes, webhooks, ledger
constraints. Keep cross-cutting "billable event" definitions co-located.
"""
