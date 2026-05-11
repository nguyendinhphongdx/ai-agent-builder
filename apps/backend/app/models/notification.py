"""Inbox notification + per-user channel preference.

Notification ``type`` strings are kept as TEXT (not enum) so a new
event source can ship without a migration. Convention:
``<resource>.<event>`` — e.g. ``workflow.failed``, ``kb.processed``,
``trigger.email.received``. Keep them stable; FE filters by prefix.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin

# Canonical type strings — import these instead of bare strings to
# get type-check coverage when callers mistype an event name.
TYPE_WORKFLOW_FAILED = "workflow.failed"
TYPE_WORKFLOW_SUCCEEDED = "workflow.succeeded"
TYPE_KB_PROCESSED = "kb.processed"
TYPE_KB_FAILED = "kb.failed"
TYPE_MEMBER_INVITED = "member.invited"
TYPE_PAYMENT_SUCCEEDED = "payment.succeeded"
TYPE_PAYMENT_FAILED = "payment.failed"
TYPE_TRIGGER_EMAIL = "trigger.email.received"
TYPE_QUOTA_WARNING = "quota.warning"


class Notification(Base, UUIDMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    type: Mapped[str] = mapped_column(String(64), primary_key=True)
    in_app: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    push: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
