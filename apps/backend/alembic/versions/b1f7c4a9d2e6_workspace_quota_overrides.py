"""Workspace-level quota soft caps.

Adds two optional override columns to the ``workspaces`` table so an
org admin can bound a single workspace's consumption without changing
the parent org's plan or paying tier.

  monthly_token_quota_override     int | null
  monthly_kb_query_quota_override  int | null

NULL = no cap, share the org pool freely (default for every existing
row, so this migration is zero-impact on consumption).

Billing model stays org-as-payer: this only changes the *check* path
inside ``quota.py`` — the org's Stripe subscription still drives the
metered overage, not anything per-workspace.

Revision ID: b1f7c4a9d2e6
Revises: o0e3f6a2b4c5
Create Date: 2026-05-15 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1f7c4a9d2e6"
down_revision: Union[str, None] = "o0e3f6a2b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workspaces",
        sa.Column("monthly_token_quota_override", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "workspaces",
        sa.Column("monthly_kb_query_quota_override", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("workspaces", "monthly_kb_query_quota_override")
    op.drop_column("workspaces", "monthly_token_quota_override")
