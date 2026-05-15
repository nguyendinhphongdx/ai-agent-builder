"""Composite (created_at, id) cursor for the metered billing reporter.

The reporter walks ``usage_events`` to ship LLM-token totals to
Stripe each tick. The cursor was previously ``last_reported_event_id``
alone — but UUIDv4 ordering is lexicographic, not temporal, so an
event inserted right after the cursor with a *smaller* random id
gets silently skipped (or shipped twice on a retry).

Add ``org_subscriptions.last_reported_event_created_at`` so the
reporter can use ``(created_at, id) > (cursor_ts, cursor_id)`` —
strictly monotonic on (clock, tiebreaker).

Backfill: copy each existing cursor's created_at from the
``usage_events`` row it references. Rows whose cursor id no longer
points to a real event get NULL (which the reporter treats as
"start from the beginning" — first sweep ships everything to date,
Stripe dedupes via idempotency_key).

Revision ID: e4i1f7d2g5b9
Revises: d3h0e6c1f4a8
Create Date: 2026-05-15 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e4i1f7d2g5b9"
down_revision: Union[str, None] = "d3h0e6c1f4a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "org_subscriptions",
        sa.Column(
            "last_reported_event_created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
    )
    # Backfill from usage_events. Subquery so we update in one pass.
    op.execute(
        """
        UPDATE org_subscriptions os
        SET    last_reported_event_created_at = ue.created_at
        FROM   usage_events ue
        WHERE  os.last_reported_event_id IS NOT NULL
        AND    ue.id = os.last_reported_event_id
        """
    )


def downgrade() -> None:
    op.drop_column("org_subscriptions", "last_reported_event_created_at")
