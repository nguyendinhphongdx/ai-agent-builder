"""Frozen KB content shipped with template versions.

When a template is published with ``include_kb_content=True``, the
author's KB documents + chunks (content + embedding) are frozen into
these tables, scoped to the AgentTemplateVersion. Forking restores
them into the buyer's namespace.

We don't reuse `documents` / `document_chunks` directly because those
have ``user_id`` ownership semantics; template content has no user.
The frozen rows live attached to the version and clone out at fork.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base


class AgentTemplateKbDocument(Base):
    """A frozen document inside a template version's bundled KB content."""

    __tablename__ = "agent_template_kb_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_template_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Index into snapshot.knowledge_bases[] — tells fork which target KB
    # shell to attach this document to.
    kb_snapshot_index: Mapped[int] = mapped_column(Integer, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    chunks: Mapped[list["AgentTemplateKbChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="AgentTemplateKbChunk.chunk_index",
    )


class AgentTemplateKbChunk(Base):
    """A frozen chunk of a template's KB document — content + embedding."""

    __tablename__ = "agent_template_kb_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    template_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_template_kb_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    # Vector dim is per-KB (lives in the embedding_dimensions field on the
    # KB snapshot). We store it un-typed so the same table can carry
    # chunks from KBs with different dims.
    embedding = mapped_column(Vector(), nullable=True)
    data: Mapped[dict] = mapped_column("data", JSONB, default=dict)

    document: Mapped[AgentTemplateKbDocument] = relationship(back_populates="chunks")
