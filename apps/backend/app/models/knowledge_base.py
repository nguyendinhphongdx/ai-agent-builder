import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base, TimestampMixin, UUIDMixin


class KnowledgeBase(Base, UUIDMixin, TimestampMixin):
    """Model knowledge base cho RAG - cấu hình embedding, chunking và retrieval."""
    __tablename__ = "knowledge_bases"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Multi-tenancy boundary. NOT NULL since Phase 1.1 step 4.
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Cấu hình embedding
    embedding_provider: Mapped[str] = mapped_column(String(50), default="openai")
    embedding_model: Mapped[str] = mapped_column(String(100), default="text-embedding-3-small")
    embedding_dimensions: Mapped[int] = mapped_column(Integer, default=1536)  # Số chiều vector embedding

    # Cấu hình chia nhỏ tài liệu (chunking)
    chunk_size: Mapped[int] = mapped_column(Integer, default=1000)  # Kích thước mỗi chunk (ký tự)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=200)  # Số ký tự chồng lấp giữa các chunk
    chunk_strategy: Mapped[str] = mapped_column(String(50), default="recursive")  # Chiến lược chia: "recursive", "character"

    # Cấu hình truy xuất (retrieval)
    retrieval_top_k: Mapped[int] = mapped_column(Integer, default=5)  # Số chunk trả về khi tìm kiếm
    retrieval_score_threshold: Mapped[float] = mapped_column(Float, default=0.7)  # Ngưỡng điểm tương đồng tối thiểu
    # "vector" = pgvector cosine-distance only (old behavior).
    # "hybrid" = BM25 ∪ vector fused via Reciprocal Rank Fusion.
    #   - Better recall for short / keyword-heavy queries (vector
    #     embeddings often miss literal token matches).
    #   - One extra index scan per query — negligible vs the
    #     embedding compute on the query side.
    # Default is "hybrid" — existing KBs improve on the next query.
    search_mode: Mapped[str] = mapped_column(
        String(20), default="hybrid", server_default="hybrid", nullable=False
    )

    # Optional reranker stage (Phase 2.1 Block 2). NULL = disabled,
    # retriever returns hybrid/vector results directly. When set,
    # retrieve() oversamples ~3× the final top_n, sends candidates
    # to the named provider, returns the top rerank_top_n by relevance.
    rerank_provider: Mapped[str | None] = mapped_column(String(50))
    rerank_model: Mapped[str | None] = mapped_column(String(100))
    rerank_top_n: Mapped[int] = mapped_column(
        Integer, default=5, server_default="5", nullable=False
    )

    # Parent-child chunking (Phase 2.1 Block 3). 0 = disabled (legacy
    # single-level chunking). >0 = enabled + value is the parent
    # chunk size in characters. ``chunk_size`` continues to govern
    # small (level=0) chunks. Typical config: chunk_size=200,
    # parent_chunk_size=1000.
    parent_chunk_size: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )

    # Bộ đếm thống kê
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )
