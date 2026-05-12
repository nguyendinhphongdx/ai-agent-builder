"""Slack inbound trigger configuration.

Binds a workflow to a Slack event stream. The /api/slack/events
receiver verifies the Slack signature, decodes the event, and
dispatches a workflow run for every matching trigger.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base, TimestampMixin, UUIDMixin

# v1 event types — extend as workflows want more granularity.
SLACK_EVENT_APP_MENTION = "app_mention"
SLACK_EVENT_MESSAGE = "message"
SLACK_EVENT_SLASH_COMMAND = "slash_command"


class SlackTrigger(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "slack_triggers"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slack_team_id: Mapped[str] = mapped_column(String(64), nullable=False)
    filter_event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    filter_channel_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    filter_command: Mapped[str | None] = mapped_column(String(64), nullable=True)
    filter_keyword: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    workflow: Mapped["Workflow"] = relationship()
