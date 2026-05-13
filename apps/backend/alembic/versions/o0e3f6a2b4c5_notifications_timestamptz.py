"""notifications + notification_preferences: timestamps → TIMESTAMPTZ

Original ``i4y7z0u6v8w9_notifications`` migration created
``notifications.created_at`` / ``read_at`` and
``notification_preferences.updated_at`` as
``TIMESTAMP WITHOUT TIME ZONE`` because the model declared bare
``Mapped[datetime]`` without ``TIMESTAMP(timezone=True)``. Workflow
runner posts ``datetime.now(timezone.utc)`` (offset-aware) which
asyncpg rejects against a naive column:

    DataError: invalid input for query argument $9: ... can't
    subtract offset-naive and offset-aware datetimes

Postgres can convert in place — UTC offsets attach without a
rewrite. Mirror the pattern used by every other table in the
schema (audit_logs, agents, etc. all use TIMESTAMPTZ).

Revision ID: o0e3f6a2b4c5
Revises: n9d2e5z1a3b4
Create Date: 2026-05-13 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "o0e3f6a2b4c5"
down_revision: Union[str, None] = "n9d2e5z1a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # USING ... AT TIME ZONE 'UTC' — interpret existing naive values
    # as UTC (which they were, per workflow_runner stamping UTC) and
    # attach the offset. No data rewrite — Postgres updates the
    # column type metadata in place.
    op.execute(
        "ALTER TABLE notifications "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE notifications "
        "ALTER COLUMN read_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING read_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE notification_preferences "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
    # Add server defaults for the columns the app expects to default
    # at INSERT time (mirrors the new ``server_default=func.now()`` in
    # the model).
    op.execute(
        "ALTER TABLE notifications ALTER COLUMN created_at SET DEFAULT now()"
    )
    op.execute(
        "ALTER TABLE notification_preferences "
        "ALTER COLUMN updated_at SET DEFAULT now()"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE notifications ALTER COLUMN created_at DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE notification_preferences ALTER COLUMN updated_at DROP DEFAULT"
    )
    op.execute(
        "ALTER TABLE notifications "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE notifications "
        "ALTER COLUMN read_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING read_at AT TIME ZONE 'UTC'"
    )
    op.execute(
        "ALTER TABLE notification_preferences "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING updated_at AT TIME ZONE 'UTC'"
    )
