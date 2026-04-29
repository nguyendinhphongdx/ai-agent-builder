"""agent_templates.include_kb_content + frozen kb tables

Revision ID: l1b3c9e7d5f2
Revises: k0a2b8d6f4e1
Create Date: 2026-04-29 17:30:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision: str = "l1b3c9e7d5f2"
down_revision: Union[str, None] = "k0a2b8d6f4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-template opt-in. Default false → existing publish flow unchanged.
    op.add_column(
        "agent_templates",
        sa.Column(
            "include_kb_content",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # ── Frozen KB content per template version ──────────────────────
    # Mirrors the live documents/document_chunks hierarchy. Chunks ship
    # with both content and embedding so a fork can read them straight
    # without a re-ingest, *if* the buyer's embedding provider matches.
    # If providers differ, retrieval at chat time will fail informatively
    # — the buyer can re-ingest from the same content rows by re-running
    # ingestion against their own embedding.
    op.create_table(
        "agent_template_kb_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_template_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # Which KB in snapshot.knowledge_bases[] this doc belongs to.
        sa.Column("kb_snapshot_index", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_template_kb_docs_version",
        "agent_template_kb_documents",
        ["version_id", "kb_snapshot_index"],
    )

    op.create_table(
        "agent_template_kb_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "template_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_template_kb_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        # Vector dim is per-KB; not enforced here so the same table can
        # carry chunks from KBs with different embedding dims (different
        # templates, different authors).
        sa.Column("embedding", Vector(), nullable=True),
        sa.Column(
            "data",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.create_index(
        "ix_template_kb_chunks_doc",
        "agent_template_kb_chunks",
        ["template_document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_template_kb_chunks_doc", table_name="agent_template_kb_chunks")
    op.drop_table("agent_template_kb_chunks")
    op.drop_index("ix_template_kb_docs_version", table_name="agent_template_kb_documents")
    op.drop_table("agent_template_kb_documents")
    op.drop_column("agent_templates", "include_kb_content")
