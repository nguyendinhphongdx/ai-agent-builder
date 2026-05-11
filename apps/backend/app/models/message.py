import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class Message(Base, UUIDMixin):
    """Model tin nhắn trong cuộc hội thoại, lưu nội dung, tool calls và metadata LLM."""
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Multi-tenancy boundary. Denormalised from parent conversation
    # for fast scan-free tenant filtering on hot paths (cost dashboards,
    # audit log queries). NOT NULL since Phase 1.1 step 4.
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(  # Hỗ trợ cấu trúc cây tin nhắn (branching)
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="SET NULL")
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user", "assistant", "tool", "system"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(20), default="text")  # "text", "image", "file"
    tool_calls: Mapped[dict | None] = mapped_column(JSONB)  # Danh sách tool calls từ LLM
    tool_call_id: Mapped[str | None] = mapped_column(String(255))  # ID của tool call (cho tin nhắn role="tool")
    tool_name: Mapped[str | None] = mapped_column(String(255))  # Tên tool đã thực thi
    attachments: Mapped[list] = mapped_column(JSONB, default=list)  # File đính kèm
    token_usage: Mapped[dict | None] = mapped_column(JSONB)  # Thống kê token sử dụng
    latency_ms: Mapped[int | None] = mapped_column(Integer)  # Thời gian phản hồi LLM
    llm_model: Mapped[str | None] = mapped_column(String(100))  # Model LLM đã sử dụng
    feedback: Mapped[str | None] = mapped_column(String(10))  # Đánh giá từ user: "up" hoặc "down"
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
