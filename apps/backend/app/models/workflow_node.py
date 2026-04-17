import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class WorkflowNode(Base, UUIDMixin):
    """Model node trong workflow - đại diện cho một bước xử lý với vị trí trên canvas."""
    __tablename__ = "workflow_nodes"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "llm", "tool", "condition", "input", "output"
    label: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)  # Cấu hình riêng theo node_type
    position_x: Mapped[float] = mapped_column(Float, default=0)  # Tọa độ X trên canvas
    position_y: Mapped[float] = mapped_column(Float, default=0)  # Tọa độ Y trên canvas
    width: Mapped[float | None] = mapped_column(Float)
    height: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="nodes")
