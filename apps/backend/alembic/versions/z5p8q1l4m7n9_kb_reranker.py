"""KB reranker config (Phase 2.1 Block 2)

Adds optional rerank pipeline to knowledge_bases. When configured,
the retriever oversamples from hybrid search then asks the reranker
to score the candidates against the query — yields better top-N
quality than embedding similarity alone, especially on technical /
code-heavy corpora.

  rerank_provider  NULL = no reranking (default).
                   "cohere"  managed, low-latency, batched API.
                   "bge"     self-hosted bge-reranker-v2-m3 (future).
                   "voyage"  managed alternative (future).
  rerank_model     provider-specific model id (e.g. "rerank-3").
  rerank_top_n     final result count after reranking. Defaults to
                   retrieval_top_k so behaviour matches non-rerank
                   path when the toggle flips on.

Revision ID: z5p8q1l4m7n9
Revises: y4o7p0k3l6m8
Create Date: 2026-05-11 10:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "z5p8q1l4m7n9"
down_revision: Union[str, None] = "y4o7p0k3l6m8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_bases",
        sa.Column("rerank_provider", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        sa.Column("rerank_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "knowledge_bases",
        # NOT NULL with default — admins toggling on rerank_provider
        # without setting rerank_top_n get sensible default behaviour.
        sa.Column(
            "rerank_top_n",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("5"),
        ),
    )


def downgrade() -> None:
    op.drop_column("knowledge_bases", "rerank_top_n")
    op.drop_column("knowledge_bases", "rerank_model")
    op.drop_column("knowledge_bases", "rerank_provider")
