import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class ApiKey(Base, UUIDMixin):
    """Model API key mã hóa - lưu trữ key của các nhà cung cấp LLM bên ngoài."""
    __tablename__ = "api_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # "openai", "anthropic", ...
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # Tên hiển thị do user đặt
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)  # API key đã được mã hóa
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # Key mặc định cho provider
    last_used_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")
