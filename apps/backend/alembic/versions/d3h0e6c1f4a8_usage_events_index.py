"""Composite index on usage_events for quota rollups + metered cursor.

Quota check runs ``SUM(total_tokens) + COUNT(*) WHERE workspace_id=?
AND event_type=? AND created_at>=?`` per workspace per request. The
billing reporter scans the same table to ship overage to Stripe.
Both degrade to full scans after a few weeks of traffic without a
covering index.

CONCURRENTLY so the migration can run on a live DB without blocking
writes. Alembic needs the transaction to be off for that — handled
by ``op.create_index(..., postgresql_concurrently=True)`` combined
with a per-revision ``transactional=False`` opt-out below.

Revision ID: d3h0e6c1f4a8
Revises: c2g8d5b0e3f7
Create Date: 2026-05-15 11:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "d3h0e6c1f4a8"
down_revision: Union[str, None] = "c2g8d5b0e3f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the implicit txn so CREATE INDEX CONCURRENTLY is legal.
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_usage_events_ws_type_created",
            "usage_events",
            ["workspace_id", "event_type", "created_at"],
            postgresql_concurrently=True,
            if_not_exists=True,
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_usage_events_ws_type_created",
            table_name="usage_events",
            postgresql_concurrently=True,
            if_exists=True,
        )
