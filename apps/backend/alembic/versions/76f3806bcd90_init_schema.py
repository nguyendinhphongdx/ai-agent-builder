"""Init schema — squashed from all prior migrations.

Delegates to ``Base.metadata.create_all`` so the table+index ordering
exactly matches the SQLAlchemy model graph (autogenerate's FK ordering
broke when fanning out to a hub-of-spokes topology like
``agent_templates``).

If you need to evolve schema after this, run::

    alembic revision --autogenerate -m "your change"

Re-squashing is fine as long as no production deploy depends on the
prior chain — wipe the volume + ``alembic/versions/*`` and regenerate.

Revision ID: 76f3806bcd90
Revises:
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import pgvector.sqlalchemy  # noqa: F401 — Vector type used in models
from alembic import op

import app.models  # noqa: F401 — register every table on Base.metadata
from app.platform.db.base import Base

revision: str = "76f3806bcd90"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # Required extensions for UUIDs + pgvector. ``init/01-extensions.sql``
    # creates them at container init for first-boot, but re-asserting here
    # makes the migration self-contained (eg. fresh CI Postgres without
    # the init script).
    bind.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    bind.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "vector"')
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
