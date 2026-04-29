"""workflows.webhook_token — URL-embedded auth for public webhook triggers

Revision ID: c2d5f3e9b6a8
Revises: b1c4e2d8a5f7
Create Date: 2026-04-29 00:01:00.000000
"""
from typing import Sequence, Union
import secrets

import sqlalchemy as sa
from alembic import op


revision: str = "c2d5f3e9b6a8"
down_revision: Union[str, None] = "b1c4e2d8a5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add nullable first so we can backfill, then enforce NOT NULL.
    op.add_column(
        "workflows",
        sa.Column("webhook_token", sa.String(length=64), nullable=True),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id FROM workflows")).fetchall()
    for row in rows:
        conn.execute(
            sa.text("UPDATE workflows SET webhook_token = :tok WHERE id = :id"),
            {"tok": secrets.token_urlsafe(32), "id": row.id},
        )

    op.alter_column("workflows", "webhook_token", nullable=False)
    op.create_index(
        "ix_workflows_webhook_token",
        "workflows",
        ["webhook_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_workflows_webhook_token", table_name="workflows")
    op.drop_column("workflows", "webhook_token")
