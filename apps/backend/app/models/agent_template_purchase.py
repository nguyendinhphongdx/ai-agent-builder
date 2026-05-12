"""Audit row for a fork — created for both free and paid templates."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base


class AgentTemplatePurchase(Base):
    """One record per fork. Free forks land here with ``price_paid_cents=0``
    so the audit trail is uniform regardless of payment.

    For paid templates the row goes through ``pending → paid`` via the Stripe
    webhook (V2). V1 only exercises free forks where status starts as ``paid``
    immediately.
    """

    __tablename__ = "agent_template_purchases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_template_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    price_paid_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(20), default="paid")  # pending|paid|refunded|failed
    # 'stripe' for USD/EUR/etc., 'momo' for VND. Free forks default to 'stripe'
    # for historical reasons (column has a server default) — they don't actually
    # exercise either provider.
    provider: Mapped[str] = mapped_column(
        String(20), default="stripe", server_default="stripe", nullable=False
    )
    # Provider-issued id used by the webhook handler to find this row.
    # Stripe: Checkout Session id (until checkout.session.completed swaps it
    # for the PaymentIntent id). MoMo: `requestId` we send at create time.
    provider_transaction_id: Mapped[str | None] = mapped_column(String(255))

    purchased_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )
    refunded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # Author-side settlement timestamp — flips when the platform actually
    # pays out to the author. Stripe destination-charge rows are settled
    # at payment time (Stripe routes funds directly); MoMo rows stay
    # ``None`` until ops marks them via /admin/purchases/{id}/settle.
    settled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # Free-text reference for the bank transfer / Stripe payout id, so
    # support can match a row to a real-world remittance later.
    settlement_reference: Mapped[str | None] = mapped_column(String(255))
