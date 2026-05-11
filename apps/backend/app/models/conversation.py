import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Conversation(Base, UUIDMixin, TimestampMixin):
    """Model cuộc hội thoại giữa user và agent, theo dõi thống kê tin nhắn và token."""
    __tablename__ = "conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Multi-tenancy boundary. Pinned from the agent's workspace at
    # conversation-create time. NOT NULL since Phase 1.1 step 4.
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255))
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)  # Ghim cuộc hội thoại lên đầu
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # Ẩn khỏi danh sách
    summary: Mapped[str | None] = mapped_column(Text)  # Tóm tắt nội dung (tự động tạo)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)  # Bộ đếm tổng tin nhắn
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)  # Bộ đếm tổng token đã sử dụng
    data: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    last_message_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    agent: Mapped["Agent"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
