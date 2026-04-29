"""Audit row for a fork — created for both free and paid templates."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


from app.db.base import Base


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
    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(255))

    purchased_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )
    refunded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
