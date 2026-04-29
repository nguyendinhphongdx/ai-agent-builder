"""workflow_runs.is_partial flag

Revision ID: b1c4e2d8a5f7
Revises: a72f5e1c8d44
Create Date: 2026-04-29 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1c4e2d8a5f7"
down_revision: Union[str, None] = "a72f5e1c8d44"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflow_runs",
        sa.Column(
            "is_partial",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("workflow_runs", "is_partial")
