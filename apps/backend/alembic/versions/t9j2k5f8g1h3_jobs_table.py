"""jobs table (Phase 1.2 — background work tracking)

Wraps the existing dispatcher-RabbitMQ pipeline with a database
record per job so we can:
  - dedupe via ``idempotency_key`` (Redis SETNX is the fast path;
    this column is the durable backstop after the Redis key expires)
  - inspect DLQ from the dashboard (no need to log into RabbitMQ UI)
  - poll status from the frontend
  - replay failed jobs without re-running the calling code

Revision ID: t9j2k5f8g1h3
Revises: s8i1j4e7f9g2
Create Date: 2026-05-11 04:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "t9j2k5f8g1h3"
down_revision: Union[str, None] = "s8i1j4e7f9g2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        # NULLABLE: some jobs are system-scope (cron tick, cleanup) and
        # don't belong to a tenant. NULL workspace_id rows are filtered
        # out of every workspace-scoped query.
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        # queued -> running -> completed | failed | dead
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'queued'")),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        # Dispatcher message id — links back to the RabbitMQ message
        # for cross-system debugging. Set when enqueue succeeds.
        sa.Column("dispatcher_message_id", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
    )
    # Workspace dashboard listing (most recent first).
    op.create_index(
        op.f("ix_jobs_workspace_id_created_at"),
        "jobs",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    # Admin DLQ query — "all failed/dead across the platform".
    op.create_index(
        op.f("ix_jobs_status_created_at"),
        "jobs",
        ["status", sa.text("created_at DESC")],
        unique=False,
    )
    op.create_index(
        op.f("ix_jobs_job_type_created_at"),
        "jobs",
        ["job_type", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_jobs_job_type_created_at"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status_created_at"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_workspace_id_created_at"), table_name="jobs")
    op.drop_table("jobs")
