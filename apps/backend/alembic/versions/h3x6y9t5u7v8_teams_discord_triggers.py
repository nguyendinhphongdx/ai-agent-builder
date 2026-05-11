"""teams_triggers + discord_triggers tables (Phase 2.4 Block 4)

Teams uses HMAC-SHA256 with a per-webhook shared secret (the admin
who created the outgoing webhook in Teams pastes the secret here at
trigger create time, Fernet-encrypted at rest).

Discord uses Ed25519 signatures. The bot's public key is required
to verify; we store it plaintext (it's not secret) alongside the
application id.

Revision ID: h3x6y9t5u7v8
Revises: g2w5x8s4t6u7
Create Date: 2026-05-11 18:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "h3x6y9t5u7v8"
down_revision: Union[str, None] = "g2w5x8s4t6u7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        # HMAC shared secret — Teams shows this once when the
        # outgoing webhook is created; admin pastes it here.
        sa.Column("hmac_secret_enc", sa.Text(), nullable=False),
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
    op.create_index(
        "ix_teams_triggers_workflow",
        "teams_triggers",
        ["workflow_id"],
        unique=False,
    )

    op.create_table(
        "discord_triggers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("discord_application_id", sa.String(length=64), nullable=False),
        # Ed25519 public key — 64 hex chars. NOT secret; we still
        # store per-trigger so multi-bot setups don't collide.
        sa.Column("discord_public_key", sa.String(length=128), nullable=False),
        # Slash command name (without leading slash).
        sa.Column("filter_command", sa.String(length=64), nullable=True),
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
    # Discord dispatcher routes by application id — keep that fast.
    op.create_index(
        "ix_discord_triggers_app",
        "discord_triggers",
        ["discord_application_id"],
        unique=False,
    )
    op.create_index(
        "ix_discord_triggers_workflow",
        "discord_triggers",
        ["workflow_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_discord_triggers_workflow", table_name="discord_triggers")
    op.drop_index("ix_discord_triggers_app", table_name="discord_triggers")
    op.drop_table("discord_triggers")
    op.drop_index("ix_teams_triggers_workflow", table_name="teams_triggers")
    op.drop_table("teams_triggers")
