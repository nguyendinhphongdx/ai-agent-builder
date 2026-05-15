"""Stripe webhook event idempotency log.

One row per processed Stripe event id, used by the webhook router
with INSERT … ON CONFLICT DO NOTHING to dedupe Stripe retries and
re-deliveries.

Revision ID: c2g8d5b0e3f7
Revises: b1f7c4a9d2e6
Create Date: 2026-05-15 11:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c2g8d5b0e3f7"
down_revision: Union[str, None] = "b1f7c4a9d2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stripe_webhook_events",
        sa.Column("event_id", sa.String(length=255), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "received_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
