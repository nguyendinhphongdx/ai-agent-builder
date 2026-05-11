"""Background job tracker — pairs every dispatcher-enqueued task with a
database row so we can dedupe, poll status, and surface DLQ to the UI."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


# State machine (one direction):
#   queued → running → completed
#                    → failed → (retry → running) | (max_attempts → dead)
JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"  # retryable
JOB_STATUS_DEAD = "dead"  # exhausted retries

JOB_TERMINAL_STATUSES = (JOB_STATUS_COMPLETED, JOB_STATUS_DEAD)


class Job(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "jobs"
    __table_args__ = (
        # Idempotency dedup at the durable layer. Redis SETNX is the
        # fast path; this constraint catches collisions when the Redis
        # key has already expired but the row still exists.
        UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
    )

    # Tenant scope. NULL for system-level jobs (cron ticks, platform
    # cleanup, …) that aren't tied to a workspace.
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # Who kicked this off. NULL for system-initiated jobs.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Dotted identifier — ``"kb.ingest.document"``, ``"workflow.run"``,
    # ``"webhook.deliver"``. Mirrors the dispatcher's ``event`` field.
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Caller-supplied dedup key. ``f"kb.ingest:{doc_id}"`` style.
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=JOB_STATUS_QUEUED,
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The dispatcher's RabbitMQ message id — set after publish succeeds.
    # Lets ops correlate a Job row with a queue entry when triaging.
    dispatcher_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
