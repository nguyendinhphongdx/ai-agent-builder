"""KB connectors (Phase 2.1 Block 4)

Adds per-KB external-source configurations. A connector defines how
the platform pulls documents from somewhere else (S3 bucket, Google
Drive folder, Notion workspace, local filesystem) into the KB.

  kb_connectors (
    id, knowledge_base_id, connector_type, name,
    config JSONB,            -- non-secret config (bucket, prefix, …)
    credentials_encrypted,   -- Fernet-encrypted JSON blob
    sync_cursor JSONB,       -- provider-specific resume point
    last_sync_at, last_error TEXT,
    is_active BOOLEAN,
    created_by, created_at, updated_at
  )

Multiple connectors per KB allowed (e.g. two S3 buckets). Sync runs
keep their resume point in ``sync_cursor`` so subsequent runs are
delta-only when the provider supports it.

Revision ID: b7r0s3n6o9p1
Revises: a6q9r2m5n8o0
Create Date: 2026-05-11 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b7r0s3n6o9p1"
down_revision: Union[str, None] = "a6q9r2m5n8o0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kb_connectors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("knowledge_base_id", sa.UUID(), nullable=False),
        # "s3" | "gcs" | "gdrive" | "notion" | "local_fs" | …
        # Stored as String so adding a provider is a code change,
        # not a migration.
        sa.Column("connector_type", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Fernet-encrypted JSON. NULL for connectors that don't need
        # secrets (e.g. local_fs in single-tenant dev).
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column(
            "sync_cursor",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_sync_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
        sa.ForeignKeyConstraint(
            ["knowledge_base_id"],
            ["knowledge_bases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_kb_connectors_knowledge_base_id"),
        "kb_connectors",
        ["knowledge_base_id"],
        unique=False,
    )
    # Index on (is_active, last_sync_at) for the scheduler tick that
    # picks "active connectors to fire next".
    op.create_index(
        op.f("ix_kb_connectors_due"),
        "kb_connectors",
        ["is_active", "last_sync_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_kb_connectors_due"), table_name="kb_connectors")
    op.drop_index(
        op.f("ix_kb_connectors_knowledge_base_id"), table_name="kb_connectors"
    )
    op.drop_table("kb_connectors")
