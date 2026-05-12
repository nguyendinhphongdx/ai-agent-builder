"""plugins table (P3.1 MVP)

Persisted record of every plugin installed in a workspace. Holds
the parsed manifest as JSONB so the registry never has to re-parse
plugin.yaml at every request. Sandboxing + subprocess execution
land in a follow-up — this revision only ships *registration*.

Revision ID: k6a9b2w8x0y1
Revises: j5z8a1v7w9x0
Create Date: 2026-05-12 11:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "k6a9b2w8x0y1"
down_revision: Union[str, None] = "j5z8a1v7w9x0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plugins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        # Identity. ``slug`` is the manifest's ``id`` field, version
        # is its ``version``. Same plugin at different versions are
        # distinct rows; only one can be ``active`` per workspace.
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        # Runtime — "python" | "nodejs" | "docker". Determines how
        # the loader (future) spins up the plugin.
        sa.Column("runtime", sa.String(length=32), nullable=False),
        # Full parsed manifest payload (capabilities, permissions,
        # schema) cached so we don't re-parse plugin.yaml at every
        # invocation.
        sa.Column(
            "manifest",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        # "active" | "disabled" | "error". The plugin daemon (future)
        # will flip to "error" on crash so the UI can surface it.
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "installed_at",
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
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "slug", "version", name="uq_plugin_ws_slug_version"
        ),
    )
    op.create_index(
        "ix_plugins_workspace",
        "plugins",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_plugins_workspace", table_name="plugins")
    op.drop_table("plugins")
