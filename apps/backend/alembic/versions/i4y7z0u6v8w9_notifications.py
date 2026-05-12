"""notifications + notification_preferences (P3.5 Block 1)

Persistent inbox layer on top of the existing socket-relay
(`app.modules.runtime.notifications.service`). Each user has rows here that survive
session close; the bell-icon UI reads from them. Real-time push is
fire-and-forget on top, not the source of truth.

Why two tables:
  notifications              — the inbox rows themselves
  notification_preferences   — per-(user, type) channel opt-ins
                               (in_app / email / push). Composite PK
                               (user_id, type) so adding a new
                               type doesn't require a migration.

Revision ID: i4y7z0u6v8w9
Revises: h3x6y9t5u7v8
Create Date: 2026-05-11 19:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "i4y7z0u6v8w9"
down_revision: Union[str, None] = "h3x6y9t5u7v8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        # NULL = platform-wide (e.g. "Welcome to AgentForge"); set =
        # scoped to one tenant so workspace switcher hides it
        # outside that context.
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        # Free-form type tag — "workflow.failed", "member.invited",
        # "payment.succeeded", "kb.processed", "trigger.email.received"…
        # Kept as TEXT not enum so adding a new type is a code change.
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        # Deep link the bell-icon row jumps to. Relative path
        # (e.g. "/workflows/abc/runs/xyz") so the FE can prefix the
        # locale once i18n ships.
        sa.Column("link_url", sa.String(length=512), nullable=True),
        # Free-form extras the FE may inline (e.g. severity, agent
        # name, retry count). Tiny JSONB; not for huge payloads.
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Inbox query is "rows for me, newest first". Composite covers it.
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )
    # Unread count + filter is the bell-icon hot path. Partial
    # index keeps it tiny — most rows are read soon after creation.
    op.create_index(
        "ix_notifications_user_unread",
        "notifications",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text("read_at IS NULL"),
    )

    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column(
            "in_app",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "email",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "push",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "type"),
    )


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_table("notifications")
