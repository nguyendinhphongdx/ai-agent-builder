"""Phase 1.1 step 4 — lock workspace_id NOT NULL across every resource table.

Closes the multi-tenancy rollout. Runs ONLY after backfill_tenancy
CLI has reported zero NULL workspace_id rows across every table —
otherwise this migration fails on the first ALTER, blocking deploy.

Tables locked (13 total):
  agents, ai_credentials, personal_access_tokens, tools,
  knowledge_bases, documents, document_chunks, conversations,
  messages, workflows, workflow_nodes, workflow_edges, workflow_runs

``users.default_workspace_id`` stays NULLABLE on purpose — its FK is
``ON DELETE SET NULL`` (so the user row survives workspace deletion);
that action would conflict with NOT NULL. The auth dependency heals
NULL pointers on the next request via ``ensure_personal_workspace``.

Revision ID: s8i1j4e7f9g2
Revises: r7h9i3d6e8f0
Create Date: 2026-05-11 03:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "s8i1j4e7f9g2"
down_revision: Union[str, None] = "r7h9i3d6e8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLES = [
    "agents",
    "ai_credentials",
    "personal_access_tokens",
    "tools",
    "knowledge_bases",
    "documents",
    "document_chunks",
    "conversations",
    "messages",
    "workflows",
    "workflow_nodes",
    "workflow_edges",
    "workflow_runs",
]


def upgrade() -> None:
    # Flip every resource table's workspace_id to NOT NULL. Order
    # doesn't matter — they're independent ALTERs. Postgres will scan
    # each table to verify zero NULL rows; if backfill missed any
    # the ALTER fails and the whole migration rolls back.
    for table in _TABLES:
        op.alter_column(
            table,
            "workspace_id",
            existing_type=op.f("UUID"),
            nullable=False,
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.alter_column(
            table,
            "workspace_id",
            existing_type=op.f("UUID"),
            nullable=True,
        )
