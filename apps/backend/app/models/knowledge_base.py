import uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


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

    # Bộ đếm thống kê
    total_documents: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="knowledge_bases")
    documents: Mapped[list["Document"]] = relationship(
        back_populates="knowledge_base", cascade="all, delete-orphan"
    )
