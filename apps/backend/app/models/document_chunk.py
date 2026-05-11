import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import TIMESTAMP, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class DocumentChunk(Base, UUIDMixin):
    """Model chunk tài liệu với vector embedding cho tìm kiếm ngữ nghĩa (pgvector)."""
    __tablename__ = "document_chunks"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(  # Denormalize để query nhanh hơn
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Multi-tenancy boundary. Same denormalisation logic as
    # knowledge_base_id — avoid a JOIN on the hot RAG path.
    # NOT NULL since Phase 1.1 step 4.
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # Thứ tự chunk trong tài liệu
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Nội dung text của chunk
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding = mapped_column(Vector())  # Vector embedding, dimension tùy theo KB config
    data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Parent-child chunking (Phase 2.1 Block 3). When the KB has
    # ``parent_chunk_size > 0``, ingestion produces two levels:
    #   level=0 small chunks (~200 tokens) — embedded + searched.
    #   level=1 parent chunks (~1000 tokens) — returned to the LLM
    #           after a small-chunk hit. Self-FK + CASCADE so deleting
    #           a parent purges its children.
    # NULL parent_chunk_id + level=0 = legacy single-level chunk.
    parent_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    chunk_level: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="chunks")
