"""agent share token + settings

Revision ID: a72f5e1c8d44
Revises: f3a91d4c2b58
Create Date: 2026-04-28 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "a72f5e1c8d44"
down_revision: Union[str, None] = "f3a91d4c2b58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("share_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "agents",
        sa.Column(
            "share_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        op.f("ix_agents_share_token"),
        "agents",
        ["share_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agents_share_token"), table_name="agents")
    op.drop_column("agents", "share_settings")
    op.drop_column("agents", "share_token")
