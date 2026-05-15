"""Per-call telemetry — one row per LLM call / KB query / tool execution.

Distinct from ``audit_logs`` (security / compliance events) and
``jobs`` (background-task tracking). usage_events is the *billing
and analytics* signal.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base, UUIDMixin

# Canonical event_type strings. Keep in sync with the service-layer
# helpers; new types are a code change, not a migration.
EVENT_LLM_CALL = "llm.call"
EVENT_KB_QUERY = "kb.query"
EVENT_TOOL_CALL = "tool.call"
EVENT_EMBED_BATCH = "embed.batch"

ALL_USAGE_EVENT_TYPES = (
    EVENT_LLM_CALL,
    EVENT_KB_QUERY,
    EVENT_TOOL_CALL,
    EVENT_EMBED_BATCH,
)


class UsageEvent(Base, UUIDMixin):
    __tablename__ = "usage_events"
    __table_args__ = (
        # Quota rollup hot path: SUM(total_tokens) and COUNT(*) WHERE
        # workspace_id = ? AND event_type = ? AND created_at >= ?.
        # Without this index every quota check degrades to a full scan
        # once the table grows past a few weeks of traffic.
        Index(
            "ix_usage_events_ws_type_created",
            "workspace_id",
            "event_type",
            "created_at",
        ),
        # Metered-billing cursor: WHERE workspace_id IN (...) AND
        # event_type = 'llm.call' AND (created_at, id) > (?, ?).
        # Same index covers it because created_at is the most-selective
        # range column.
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )
    workflow_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    # ``provider/model`` format mirrors how agents.model_id is stored.
    # Keep the slash-split happening at the call site so the column
    # stays canonical.
    model: Mapped[str | None] = mapped_column(String(128))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(precision=10, scale=6))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    data: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=False
    )
