"""add processing_phase + processing_progress to documents

Revision ID: e8a2c1f4b673
Revises: db924f2d3626
Create Date: 2026-04-23 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e8a2c1f4b673"
down_revision: Union[str, None] = "db924f2d3626"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("processing_phase", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("processing_progress", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "processing_progress")
    op.drop_column("documents", "processing_phase")
