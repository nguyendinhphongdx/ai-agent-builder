import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class WorkflowRun(Base, UUIDMixin):
    """Model lưu lịch sử thực thi workflow - dữ liệu I/O, token và chi phí."""
    __tablename__ = "workflow_runs"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(  # Conversation kích hoạt workflow (nếu có)
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL")
    )

    # Trạng thái thực thi: "running" -> "completed" / "failed"
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    # True khi chỉ chạy 1 node (Execute Step trong NDV) — không phải full workflow.
    is_partial: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)  # Dữ liệu đầu vào
    output_data: Mapped[dict | None] = mapped_column(JSONB)  # Kết quả đầu ra
    error_message: Mapped[str | None] = mapped_column(Text)
    node_executions: Mapped[list] = mapped_column(JSONB, default=list)  # Log thực thi từng node

    # Thống kê chi phí
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(10, 6), default=0)  # Chi phí ước tính (USD)

    # Thời gian thực thi
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="runs")
