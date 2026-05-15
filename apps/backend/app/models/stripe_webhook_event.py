"""Idempotency log for processed Stripe webhook events.

Stripe retries any non-2xx delivery, and re-delivers on transient
network failures even when the receiver returned 2xx. Without
deduplication the same event can mutate state twice:

  customer.subscription.updated → upsert is naturally idempotent OK
  invoice.payment_failed        → status flip OK
  account.updated               → mirror flags OK

— but extending the pipeline (dunning emails, usage credits) is one
new handler away from a double-mutate. A single PK table on
``event.id`` is the standard fix.

Insert is run *inside* the handler's transaction with
``INSERT … ON CONFLICT DO NOTHING``: a successful handler commits
both the row and its side effects together; a failing handler rolls
both back so Stripe's next retry runs the handler again from scratch.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    # Stripe event ids are short strings like ``evt_1Q4F2x…``. The PK
    # makes the dedupe ``ON CONFLICT`` deterministic and fast.
    event_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    # event.type for observability; not part of the dedupe key but
    # useful when grepping the table to see "which events have we
    # actually received".
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
