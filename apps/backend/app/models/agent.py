import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base, TimestampMixin, UUIDMixin


class AgentTool(Base):
    """Bảng trung gian liên kết agent với tool (quan hệ N-N)."""
    __tablename__ = "agent_tools"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )


class AgentKnowledgeBase(Base):
    """Bảng trung gian liên kết agent với knowledge base (quan hệ N-N)."""
    __tablename__ = "agent_knowledge_bases"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), primary_key=True
    )
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )


class Agent(Base, UUIDMixin, TimestampMixin):
    """Model AI agent - cấu hình LLM, system prompt, và các công cụ đi kèm."""
    __tablename__ = "agents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Multi-tenancy boundary. NOT NULL since Phase 1.1 step 4. Service
    # queries that scope by tenant filter on this column, NOT on
    # ``user_id`` (which only identifies the creator within a workspace).
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)  # Prompt hệ thống định nghĩa hành vi agent
    # Model identifier theo format "provider/model" — VD "openai/gpt-4o", "anthropic/claude-sonnet-4-20250514"
    model_id: Mapped[str] = mapped_column(String(150), nullable=False, default="openai/gpt-4o")
    credential_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_credentials.id", ondelete="SET NULL"), nullable=True, index=True
    )
    llm_config: Mapped[dict] = mapped_column(JSONB, default=dict)  # Cấu hình LLM: temperature, max_tokens, ...
    welcome_message: Mapped[str | None] = mapped_column(Text)  # Tin nhắn chào mừng khi bắt đầu hội thoại
    max_turns: Mapped[int] = mapped_column(Integer, default=50)  # Giới hạn số lượt trao đổi tối đa
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)  # "draft" hoặc "active"
    kb_retrieval_mode: Mapped[str] = mapped_column(String(20), default="tool")  # "auto" hoặc "tool"

    # Share / embed channel — when share_token is set, /api/share/{token}/* is
    # publicly callable (no auth) and the embed widget can render this agent.
    # Rotate by overwriting; revoke by setting to NULL.
    share_token: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )
    # UI/widget customisation (theme color, position, greeting, …). Free-form
    # JSON so the widget can evolve without DB migrations.
    share_settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Hub provenance — set when this agent was forked from a published template.
    # Both nullable: agents created from scratch don't have these.
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_templates.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_template_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Quan hệ
    user: Mapped["User"] = relationship(back_populates="agents")
    workspace: Mapped["Workspace | None"] = relationship(foreign_keys=[workspace_id])
    credential: Mapped["AICredential | None"] = relationship(lazy="joined")
    tools: Mapped[list["Tool"]] = relationship(secondary="agent_tools", lazy="selectin")
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(
        secondary="agent_knowledge_bases", lazy="selectin"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="agent")
