"""agent_template_purchases.settled_at + settlement_reference

Revision ID: i8e0f6b4d3c9
Revises: h7d9e5a3b2c8
Create Date: 2026-04-29 16:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "i8e0f6b4d3c9"
down_revision: Union[str, None] = "h7d9e5a3b2c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Author-side settlement — flips when the platform actually pays the
    # author (bank transfer reference goes in `settlement_reference`).
    # Stripe destination charges settle automatically via Connect; for
    # those rows we backfill `settled_at = paid_at` in the admin tool
    # so the dashboard treats them uniformly. MoMo (platform-collects)
    # rows stay unsettled until ops marks them.
    op.add_column(
        "agent_template_purchases",
        sa.Column("settled_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_template_purchases",
        sa.Column("settlement_reference", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_template_purchases", "settlement_reference")
    op.drop_column("agent_template_purchases", "settled_at")
