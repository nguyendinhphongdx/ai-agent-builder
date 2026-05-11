import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Workflow(Base, UUIDMixin, TimestampMixin):
    """Model workflow tự động hóa - đồ thị gồm các node và edge, có quản lý phiên bản."""
    __tablename__ = "workflows"

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
    agent_id: Mapped[uuid.UUID | None] = mapped_column(  # Agent gắn với workflow (tùy chọn)
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)  # Số phiên bản workflow
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)  # Workflow đang hoạt động hay không
    viewport: Mapped[dict] = mapped_column(JSONB, default=dict)  # Trạng thái viewport của canvas editor
    # URL-embedded shared secret. Public webhook callers must include this in
    # the path so leaking workflow_id alone is not enough to trigger.
    webhook_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    # Relationships
    user: Mapped["User"] = relationship()
    agent: Mapped["Agent | None"] = relationship(back_populates="workflows")
    nodes: Mapped[list["WorkflowNode"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    edges: Mapped[list["WorkflowEdge"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    runs: Mapped[list["WorkflowRun"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
