"""Scheduled trigger — pairs a workflow's ``cron_trigger`` node with
a cron expression so the platform tick can fire workflow runs on
schedule."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ScheduledTrigger(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scheduled_triggers"
    __table_args__ = (
        # Each (workflow, node) maps to at most one row. Sync from
        # workflow save relies on this for idempotent UPSERT.
        UniqueConstraint(
            "workflow_id", "node_id", name="uq_scheduled_triggers_workflow_node"
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Cron expression — parsed by croniter. Validated at the service
    # layer before insert/update (caller-supplied bad input must
    # not crash the scheduler tick).
    cron_expression: Mapped[str] = mapped_column(String(128), nullable=False)
    # IANA timezone name (``"Asia/Ho_Chi_Minh"``, ``"UTC"``). croniter
    # evaluates the expression in this zone so DST + offset are honoured.
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="UTC"
    )
    # Pre-computed next fire time — populated by the service layer
    # using croniter at insert/update + after each fire. Lets the
    # scheduler tick run a single ``WHERE next_run_at <= now()`` index
    # scan instead of evaluating cron expressions in SQL.
    next_run_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    last_run_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    # Static payload handed to the workflow at fire time — same shape
    # as the body a webhook trigger would pass.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
