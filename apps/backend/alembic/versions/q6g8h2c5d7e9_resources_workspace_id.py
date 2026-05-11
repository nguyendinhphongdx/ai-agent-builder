"""tools/KB/documents/chunks/conversations/messages workspace_id (Phase 1.1 step 2 — group B)

Six tables in one migration — the AI-resources cluster. All columns
are nullable + FK CASCADE → workspaces, matching the agents pattern.

Note: documents and document_chunks don't carry user_id today (they
inherit tenancy through their parent KB) and messages inherit through
conversations. We add workspace_id to them anyway so backfill can
stamp every row directly, avoiding a 3-level JOIN at query time
once the lock migration enables scoped queries everywhere.

Revision ID: q6g8h2c5d7e9
Revises: p5f7g1b4c6d8
Create Date: 2026-05-11 02:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "q6g8h2c5d7e9"
down_revision: Union[str, None] = "p5f7g1b4c6d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Resource tables to stamp. (table, fk_name, ix_name)
_TABLES = [
    ("tools", "fk_tools_workspace_id", "ix_tools_workspace_id"),
    (
        "knowledge_bases",
        "fk_knowledge_bases_workspace_id",
        "ix_knowledge_bases_workspace_id",
    ),
    ("documents", "fk_documents_workspace_id", "ix_documents_workspace_id"),
    (
        "document_chunks",
        "fk_document_chunks_workspace_id",
        "ix_document_chunks_workspace_id",
    ),
    (
        "conversations",
        "fk_conversations_workspace_id",
        "ix_conversations_workspace_id",
    ),
    ("messages", "fk_messages_workspace_id", "ix_messages_workspace_id"),
]


def upgrade() -> None:
    for table, fk_name, ix_name in _TABLES:
        op.add_column(table, sa.Column("workspace_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            fk_name, table, "workspaces", ["workspace_id"], ["id"], ondelete="CASCADE"
        )
        op.create_index(op.f(ix_name), table, ["workspace_id"], unique=False)


def downgrade() -> None:
    for table, fk_name, ix_name in reversed(_TABLES):
        op.drop_index(op.f(ix_name), table_name=table)
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.drop_column(table, "workspace_id")
