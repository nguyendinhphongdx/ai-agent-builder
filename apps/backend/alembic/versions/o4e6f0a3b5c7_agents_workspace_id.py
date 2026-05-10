"""agents.workspace_id (Phase 1.1 step 2 — proof of pattern)

First resource table to gain a ``workspace_id`` column. Stays NULLABLE
through the transition so existing single-tenant rows keep working
unchanged. Service-layer plumbing (default to caller's
``default_workspace_id`` on insert; filter SELECTs by the user's
member workspaces) lands as separate, reviewable changes.

Once the same pattern is applied to every resource table and a
backfill run populates the column on legacy rows, a follow-up
migration flips it to ``NOT NULL`` to lock tenancy in place.

Revision ID: o4e6f0a3b5c7
Revises: n3d5e9f2a4b6
Create Date: 2026-05-11 00:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "o4e6f0a3b5c7"
down_revision: Union[str, None] = "n3d5e9f2a4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("workspace_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_agents_workspace_id",
        "agents",
        "workspaces",
        ["workspace_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_agents_workspace_id"),
        "agents",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agents_workspace_id"), table_name="agents")
    op.drop_constraint("fk_agents_workspace_id", "agents", type_="foreignkey")
    op.drop_column("agents", "workspace_id")
