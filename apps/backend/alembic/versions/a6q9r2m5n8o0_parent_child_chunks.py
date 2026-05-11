"""Parent-child chunking (Phase 2.1 Block 3)

Adds the schema to support the small-chunk-search / large-chunk-
return pattern. Small chunks (~200 tokens) get embedded + searched;
parent chunks (~1000 tokens) get handed to the LLM for context.

  document_chunks.parent_chunk_id  Self-FK pointing to a level=1
                                   row in the same table. NULL on
                                   parents themselves + on legacy
                                   single-level chunks.
  document_chunks.chunk_level      0 = small (default, searchable).
                                   1 = parent (returned to LLM).
  knowledge_bases.parent_chunk_size 0 = disabled (legacy single-
                                   level chunking). >0 enables
                                   parent-child mode at the given
                                   parent size.

Existing data: every chunk has chunk_level=0 and parent_chunk_id
NULL after the migration — retrieval works exactly as before. New
documents ingested into KBs with parent_chunk_size>0 produce both
levels.

Revision ID: a6q9r2m5n8o0
Revises: z5p8q1l4m7n9
Create Date: 2026-05-11 11:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a6q9r2m5n8o0"
down_revision: Union[str, None] = "z5p8q1l4m7n9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("parent_chunk_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_document_chunks_parent_chunk_id",
        "document_chunks",
        "document_chunks",
        ["parent_chunk_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_document_chunks_parent_chunk_id"),
        "document_chunks",
        ["parent_chunk_id"],
        unique=False,
    )
    op.add_column(
        "document_chunks",
        sa.Column(
            "chunk_level",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column(
            "parent_chunk_size",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "parent_chunk_size")
    op.drop_column("document_chunks", "chunk_level")
    op.drop_index(
        op.f("ix_document_chunks_parent_chunk_id"), table_name="document_chunks"
    )
    op.drop_constraint(
        "fk_document_chunks_parent_chunk_id",
        "document_chunks",
        type_="foreignkey",
    )
    op.drop_column("document_chunks", "parent_chunk_id")
