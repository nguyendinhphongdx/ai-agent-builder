"""scheduled_triggers table (Phase 1.2 Block 5 — workflow cron triggers)

One row per active ``cron_trigger`` node across the platform. The
scheduler tick picks up rows where ``next_run_at <= now`` and
enqueues a workflow.run.scheduled job, then advances next_run_at
via croniter.

Lifecycle: rows are upserted whenever a workflow's graph is saved
(see ``app.scheduled_triggers.service.sync_from_workflow``). Pause
by flipping ``is_active=False``; delete when the trigger node is
removed.

Revision ID: u0k3l6g9h2i4
Revises: t9j2k5f8g1h3
Create Date: 2026-05-11 05:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "u0k3l6g9h2i4"
down_revision: Union[str, None] = "t9j2k5f8g1h3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        # The cron_trigger node inside the workflow this row mirrors.
        # Lets the scheduler pull the right node's config (timezone,
        # payload template) at fire time without scanning every node.
        sa.Column("node_id", sa.UUID(), nullable=False),
        sa.Column("cron_expression", sa.String(length=128), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default=sa.text("'UTC'")),
        sa.Column("next_run_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        # Static payload the scheduler hands to the workflow at fire
        # time. Use for "every Monday at 9am, run with input={team: 'sales'}"
        # patterns. Free-form JSON, no validation here.
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
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
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["node_id"], ["workflow_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        # Each (workflow, node) combo maps to at most one row — sync
        # function uses this for idempotent upsert.
        sa.UniqueConstraint("workflow_id", "node_id", name="uq_scheduled_triggers_workflow_node"),
    )
    # Scheduler tick query — "what fires next?".
    op.create_index(
        op.f("ix_scheduled_triggers_due"),
        "scheduled_triggers",
        ["is_active", "next_run_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_triggers_workspace_id"),
        "scheduled_triggers",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_triggers_workspace_id"), table_name="scheduled_triggers")
    op.drop_index(op.f("ix_scheduled_triggers_due"), table_name="scheduled_triggers")
    op.drop_table("scheduled_triggers")
