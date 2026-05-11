"""slack_triggers table (Phase 2.4 Block 3)

A workflow can subscribe to Slack events from one or more Slack
workspaces. Signing-secret verification uses a platform-level
secret (settings.SLACK_SIGNING_SECRET) — V1 assumes a single
Slack app distributed to orgs via OAuth; per-app signing secrets
are a future axis.

Dispatch fan-out:
  One Slack event → look up triggers by team_id × filter → enqueue
  a workflow run per matching trigger. Multiple workflows can
  react to the same event.

Revision ID: g2w5x8s4t6u7
Revises: f1v4w7r3s5t6
Create Date: 2026-05-11 17:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "g2w5x8s4t6u7"
down_revision: Union[str, None] = "f1v4w7r3s5t6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slack_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        # Slack workspace (team) id like "T012ABC". One Slack
        # workspace can be wired to many AgentForge workspaces if
        # multiple orgs share an org-level Slack.
        sa.Column("slack_team_id", sa.String(length=64), nullable=False),
        # Event type to listen to. Three v1 values:
        #   "app_mention"  the bot user is @-mentioned
        #   "message"      a channel message (filter recommended)
        #   "slash_command" a /command invocation
        sa.Column("filter_event_type", sa.String(length=32), nullable=False),
        # Restrict to one channel (NULL = all channels). For
        # slash_command this is unused — slash commands aren't
        # channel-scoped at Slack's API level.
        sa.Column("filter_channel_id", sa.String(length=64), nullable=True),
        # Slash command trigger string (with leading slash, e.g.
        # "/agent"). Only consulted when filter_event_type =
        # "slash_command".
        sa.Column("filter_command", sa.String(length=64), nullable=True),
        # Free-form keyword to require in the message body. Tiny
        # contains-match; NULL disables. Use case: only fire when
        # a message includes "urgent".
        sa.Column("filter_keyword", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"], ["workflows.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # The hot index for the event dispatcher — every Slack event
    # looks up by (team_id, event_type) so the index covers both.
    op.create_index(
        "ix_slack_triggers_team_event",
        "slack_triggers",
        ["slack_team_id", "filter_event_type"],
        unique=False,
    )
    op.create_index(
        "ix_slack_triggers_workflow",
        "slack_triggers",
        ["workflow_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_slack_triggers_workflow", table_name="slack_triggers")
    op.drop_index("ix_slack_triggers_team_event", table_name="slack_triggers")
    op.drop_table("slack_triggers")
