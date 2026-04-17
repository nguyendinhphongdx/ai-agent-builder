import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin


class WorkflowEdge(Base, UUIDMixin):
    """Model cạnh nối giữa hai node trong workflow - định nghĩa luồng dữ liệu."""
    __tablename__ = "workflow_edges"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(  # Node nguồn (đầu ra)
        UUID(as_uuid=True),
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(  # Node đích (đầu vào)
        UUID(as_uuid=True),
        ForeignKey("workflow_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_handle: Mapped[str | None] = mapped_column(String(100))  # Handle/port trên node nguồn
    target_handle: Mapped[str | None] = mapped_column(String(100))  # Handle/port trên node đích
    label: Mapped[str | None] = mapped_column(String(255))  # Nhãn hiển thị trên cạnh
    style: Mapped[dict] = mapped_column(JSONB, default=dict)  # Style CSS cho cạnh trên canvas
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="edges")
