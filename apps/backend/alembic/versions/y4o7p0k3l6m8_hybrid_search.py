"""Hybrid search foundation (Phase 2.1 Block 1)

Adds:
  - ``document_chunks.content_tsv`` — generated tsvector column
    (computed at write time, stored on disk) + GIN index for fast
    BM25-style lexical ranking.
  - ``knowledge_bases.search_mode`` — per-KB toggle between
    pure-vector and hybrid (BM25 ∪ vector via Reciprocal Rank
    Fusion). Default ``hybrid`` so existing KBs improve on the
    next query without admin action.

The tsvector uses ``simple`` dictionary — no language-specific
stemming. We index multilingual content (English / Vietnamese /
mixed) and stemming with the wrong dictionary hurts more than it
helps. If a single-language KB needs stemming later, swap the
dictionary in a follow-up migration.

Revision ID: y4o7p0k3l6m8
Revises: x3n6o9j2k5l7
Create Date: 2026-05-11 09:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "y4o7p0k3l6m8"
down_revision: Union[str, None] = "x3n6o9j2k5l7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generated tsvector column. Computed once at write time, indexed
    # via GIN — query-time cost is just the index scan + ts_rank_cd.
    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED
        """
    )
    op.create_index(
        "ix_document_chunks_content_tsv",
        "document_chunks",
        ["content_tsv"],
        postgresql_using="gin",
    )

    op.add_column(
        "knowledge_bases",
        sa.Column(
            "search_mode",
            sa.String(length=20),
            nullable=False,
            # New KBs hybrid by default. Existing rows pick up the
            # default on read since the column is now NOT NULL.
            server_default=sa.text("'hybrid'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "search_mode")
    op.drop_index("ix_document_chunks_content_tsv", table_name="document_chunks")
    op.execute("ALTER TABLE document_chunks DROP COLUMN content_tsv")
