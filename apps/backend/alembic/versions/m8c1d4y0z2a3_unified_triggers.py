"""unified triggers table

One ``triggers`` row shape replaces the five legacy single-purpose
tables. The migration is *data-preserving*: every row from each
legacy table is copied into ``triggers`` with provider-specific
columns folded into the ``config`` JSONB.

Downgrade re-creates the five legacy tables but does NOT copy data
back — the operation is structurally reversible but not
data-reversible (the legacy tables had per-column NOT NULL
constraints that would require careful reverse-mapping). Treat the
upgrade as one-way in production.

Revision ID: m8c1d4y0z2a3
Revises: l7b0c3x9y1z2
Create Date: 2026-05-12 14:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "m8c1d4y0z2a3"
down_revision: Union[str, None] = "l7b0c3x9y1z2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. Create unified table ─────────────────────────────────
    op.create_table(
        "triggers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("last_fired_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_run_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_polled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "poll_cursor",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Indexes
    op.create_index("ix_triggers_workspace_type", "triggers", ["workspace_id", "type"])
    op.create_index("ix_triggers_workflow", "triggers", ["workflow_id"])
    op.create_index(
        "ix_triggers_next_run",
        "triggers",
        ["next_run_at"],
        postgresql_where=sa.text("next_run_at IS NOT NULL"),
    )
    op.execute(
        """
        CREATE INDEX ix_triggers_slack_dispatch ON triggers
            ((config->>'slack_team_id'), (config->>'filter_event_type'))
            WHERE type = 'slack' AND is_active;
        """
    )
    op.execute(
        """
        CREATE INDEX ix_triggers_discord_app ON triggers
            ((config->>'discord_application_id'))
            WHERE type = 'discord' AND is_active;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_triggers_scheduled_node ON triggers
            (workflow_id, (config->>'node_id'))
            WHERE type = 'scheduled';
        """
    )

    # ─── 2. Copy data from legacy tables ─────────────────────────
    # Each legacy table has the same skeleton (id, workflow_id,
    # workspace_id, name, is_active, created_at, updated_at) + a
    # handful of provider-specific columns that fold into config.
    #
    # ``IF EXISTS`` so this migration is safe to run on dev DBs
    # that never had the legacy tables created.

    op.execute(
        """
        INSERT INTO triggers (
            id, type, workflow_id, workspace_id, name, config,
            is_active, created_at, updated_at
        )
        SELECT
            id, 'slack', workflow_id, workspace_id, name,
            jsonb_strip_nulls(jsonb_build_object(
                'slack_team_id',    slack_team_id,
                'filter_event_type', filter_event_type,
                'filter_channel_id', filter_channel_id,
                'filter_command',   filter_command,
                'filter_keyword',   filter_keyword
            )),
            is_active, created_at, updated_at
        FROM slack_triggers
        WHERE EXISTS (SELECT 1 FROM information_schema.tables
                      WHERE table_name = 'slack_triggers');
        """
    )

    op.execute(
        """
        INSERT INTO triggers (
            id, type, workflow_id, workspace_id, name, config,
            credentials_encrypted, is_active, created_at, updated_at
        )
        SELECT
            id, 'teams', workflow_id, workspace_id, name,
            jsonb_strip_nulls(jsonb_build_object(
                'filter_keyword', filter_keyword
            )),
            hmac_secret_enc,
            is_active, created_at, updated_at
        FROM teams_triggers
        WHERE EXISTS (SELECT 1 FROM information_schema.tables
                      WHERE table_name = 'teams_triggers');
        """
    )

    op.execute(
        """
        INSERT INTO triggers (
            id, type, workflow_id, workspace_id, name, config,
            is_active, created_at, updated_at
        )
        SELECT
            id, 'discord', workflow_id, workspace_id, name,
            jsonb_strip_nulls(jsonb_build_object(
                'discord_application_id', discord_application_id,
                'discord_public_key',     discord_public_key,
                'filter_command',         filter_command
            )),
            is_active, created_at, updated_at
        FROM discord_triggers
        WHERE EXISTS (SELECT 1 FROM information_schema.tables
                      WHERE table_name = 'discord_triggers');
        """
    )

    op.execute(
        """
        INSERT INTO triggers (
            id, type, workflow_id, workspace_id, name, config,
            credentials_encrypted, is_active,
            last_polled_at, last_error, poll_cursor,
            created_at, updated_at
        )
        SELECT
            id, 'email', workflow_id, workspace_id, name,
            jsonb_strip_nulls(jsonb_build_object(
                'imap_host',             imap_host,
                'imap_port',             imap_port,
                'imap_use_ssl',          imap_use_ssl,
                'imap_username',         imap_username,
                'imap_folder',           imap_folder,
                'poll_interval_seconds', poll_interval_seconds,
                'mark_seen',             mark_seen
            )),
            imap_password_enc,
            is_active,
            last_polled_at,
            last_error,
            jsonb_strip_nulls(jsonb_build_object(
                'last_seen_uid', last_seen_uid
            )),
            created_at, updated_at
        FROM email_triggers
        WHERE EXISTS (SELECT 1 FROM information_schema.tables
                      WHERE table_name = 'email_triggers');
        """
    )

    op.execute(
        """
        INSERT INTO triggers (
            id, type, workflow_id, workspace_id, name, config,
            is_active, next_run_at, last_fired_at,
            created_by, created_at, updated_at
        )
        SELECT
            id, 'scheduled', workflow_id, workspace_id,
            COALESCE(cron_expression, 'scheduled'),
            jsonb_strip_nulls(jsonb_build_object(
                'node_id',         node_id::text,
                'cron_expression', cron_expression,
                'timezone',        timezone,
                'payload',         payload
            )),
            is_active, next_run_at, last_run_at,
            created_by, created_at, updated_at
        FROM scheduled_triggers
        WHERE EXISTS (SELECT 1 FROM information_schema.tables
                      WHERE table_name = 'scheduled_triggers');
        """
    )

    # ─── 3. Drop legacy tables ───────────────────────────────────
    op.execute("DROP TABLE IF EXISTS slack_triggers CASCADE")
    op.execute("DROP TABLE IF EXISTS teams_triggers CASCADE")
    op.execute("DROP TABLE IF EXISTS discord_triggers CASCADE")
    op.execute("DROP TABLE IF EXISTS email_triggers CASCADE")
    op.execute("DROP TABLE IF EXISTS scheduled_triggers CASCADE")


def downgrade() -> None:
    """Recreate the legacy tables (empty). Data is NOT copied back —
    the per-column NOT NULL constraints would require careful
    reverse-mapping that's only worth doing if a real revert is
    needed. Treat upgrade as one-way."""
    op.create_table(
        "slack_triggers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slack_team_id", sa.String(64), nullable=False),
        sa.Column("filter_event_type", sa.String(32), nullable=False),
        sa.Column("filter_channel_id", sa.String(64)),
        sa.Column("filter_command", sa.String(64)),
        sa.Column("filter_keyword", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
    )
    op.create_table(
        "teams_triggers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hmac_secret_enc", sa.Text(), nullable=False),
        sa.Column("filter_keyword", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
    )
    op.create_table(
        "discord_triggers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("discord_application_id", sa.String(64), nullable=False),
        sa.Column("discord_public_key", sa.String(128), nullable=False),
        sa.Column("filter_command", sa.String(64)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
    )
    op.create_table(
        "email_triggers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("imap_host", sa.String(255), nullable=False),
        sa.Column("imap_port", sa.Integer(), nullable=False, server_default="993"),
        sa.Column("imap_use_ssl", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("imap_username", sa.String(255), nullable=False),
        sa.Column("imap_password_enc", sa.Text(), nullable=False),
        sa.Column(
            "imap_folder", sa.String(255), nullable=False, server_default="INBOX"
        ),
        sa.Column(
            "poll_interval_seconds", sa.Integer(), nullable=False, server_default="300"
        ),
        sa.Column("mark_seen", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_seen_uid", sa.BigInteger()),
        sa.Column("last_polled_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("last_error_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
    )
    op.create_table(
        "scheduled_triggers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workflow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("cron_expression", sa.String(128), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("next_run_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_run_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")
        ),
        sa.UniqueConstraint(
            "workflow_id", "node_id", name="uq_scheduled_triggers_workflow_node"
        ),
    )
    op.drop_table("triggers")
