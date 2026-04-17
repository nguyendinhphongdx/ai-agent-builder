import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class Document(Base, UUIDMixin):
    """Model tài liệu được upload vào knowledge base, theo dõi trạng thái xử lý."""
    __tablename__ = "documents"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Thông tin file
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)  # Đường dẫn lưu trữ trên server
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "pdf", "txt", "docx", ...
    file_size: Mapped[int | None] = mapped_column(BigInteger)  # Kích thước file (bytes)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    content_hash: Mapped[str | None] = mapped_column(String(64))  # SHA-256 hash để phát hiện trùng lặp

    # Thống kê sau khi xử lý
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int | None] = mapped_column(Integer)

    # Trạng thái xử lý: "pending" -> "processing" -> "completed" / "failed"
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    processing_started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    processing_completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    # Relationships
    knowledge_base: Mapped["KnowledgeBase"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
