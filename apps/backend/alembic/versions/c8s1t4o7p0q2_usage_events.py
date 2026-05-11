"""usage_events table (Phase 2.2 Block 1)

Per-call telemetry for LLM / KB / tool / embed events. One row per
billable action; aggregates power the cost dashboard + future
usage-metered billing (Phase 2.3).

Wide-and-loose: event_type is a string so adding "embed.batch",
"workflow.step", etc. is a code change not a migration. cost_usd
is NUMERIC(10,6) so we can store fractional cents accurately
(GPT-4o tokens cost ~0.0000125 each — three decimal places would
round to zero).

Revision ID: c8s1t4o7p0q2
Revises: b7r0s3n6o9p1
Create Date: 2026-05-11 13:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "c8s1t4o7p0q2"
down_revision: Union[str, None] = "b7r0s3n6o9p1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("agent_id", sa.UUID(), nullable=True),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("workflow_run_id", sa.UUID(), nullable=True),
        # "llm.call" | "kb.query" | "tool.call" | "embed.batch" | …
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        # NUMERIC(10,6) handles per-token costs as small as $0.000001.
        # Larger denominator (10) leaves room for batch costs into the
        # high $99,999 range — plenty for a single call.
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["workflow_run_id"], ["workflow_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Cost dashboard: "show this workspace's spend grouped by day/agent".
    op.create_index(
        op.f("ix_usage_events_workspace_created"),
        "usage_events",
        ["workspace_id", sa.text("created_at DESC")],
        unique=False,
    )
    # Per-agent rollups for analytics drill-downs.
    op.create_index(
        op.f("ix_usage_events_agent_created"),
        "usage_events",
        ["agent_id", sa.text("created_at DESC")],
        unique=False,
    )
    # Platform-wide event-type filtering (admin "show me every kb.query").
    op.create_index(
        op.f("ix_usage_events_type_created"),
        "usage_events",
        ["event_type", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_events_type_created"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_agent_created"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_workspace_created"), table_name="usage_events")
    op.drop_table("usage_events")
