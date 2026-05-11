"""Organization-level Stripe subscription state.

One row per org. Plan tier still lives on ``organizations.plan`` —
this row holds the *billing* state (Stripe ids, period boundaries,
status). Free-tier orgs may have no row at all; that's the implicit
default and quota guards treat ``None`` as ``plan=free``.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin

# Stripe subscription statuses we care about. Anything not in the
# "live" set is treated as no-subscription for quota purposes.
SUB_STATUS_ACTIVE = "active"
SUB_STATUS_TRIALING = "trialing"
SUB_STATUS_PAST_DUE = "past_due"
SUB_STATUS_INCOMPLETE = "incomplete"
SUB_STATUS_CANCELED = "canceled"
SUB_STATUS_UNPAID = "unpaid"

LIVE_STATUSES = (SUB_STATUS_ACTIVE, SUB_STATUS_TRIALING, SUB_STATUS_PAST_DUE)


class OrgSubscription(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "org_subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SUB_STATUS_ACTIVE)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    stripe_metered_item_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_period_start: Mapped[datetime | None] = mapped_column(nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_reported_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    last_reported_at: Mapped[datetime | None] = mapped_column(nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    organization: Mapped["Organization"] = relationship()

    @property
    def is_live(self) -> bool:
        """True iff Stripe still considers the subscription billable."""
        return self.status in LIVE_STATUSES
