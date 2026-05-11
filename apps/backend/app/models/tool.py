import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Tool(Base, UUIDMixin, TimestampMixin):
    """Model công cụ tùy chỉnh - định nghĩa input/output schema và cấu hình thực thi."""
    __tablename__ = "tools"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Multi-tenancy boundary (Phase 1.1). Nullable through transition.
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tool_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # Loại tool: "api", "function", ...
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Cấu hình riêng của tool (URL, headers, ...)
    input_schema: Mapped[dict] = mapped_column(JSONB, nullable=False)  # JSON Schema mô tả tham số đầu vào
    output_schema: Mapped[dict | None] = mapped_column(JSONB)  # JSON Schema mô tả kết quả trả về
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)  # Thời gian chờ tối đa khi thực thi

    # Relationships
    user: Mapped["User"] = relationship(back_populates="tools")
