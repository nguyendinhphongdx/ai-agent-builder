"""commerce/payments/ — three faces of the same payment rail.

  * subscriptions/  recurring billing (plans, quota, Stripe subs)
  * checkout/       one-time purchases (Stripe + MoMo gateways)
  * payouts/        author marketplace revshare

Shared Stripe SDK access is currently per-subfolder; consolidate
into a ``_client.py`` if a fourth flavour gets added.
"""
