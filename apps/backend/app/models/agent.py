import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDMixin, TimestampMixin


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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)  # Prompt hệ thống định nghĩa hành vi agent
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="openai")  # "openai" hoặc "anthropic"
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4o")
    llm_config: Mapped[dict] = mapped_column(JSONB, default=dict)  # Cấu hình LLM: temperature, max_tokens, ...
    welcome_message: Mapped[str | None] = mapped_column(Text)  # Tin nhắn chào mừng khi bắt đầu hội thoại
    max_turns: Mapped[int] = mapped_column(Integer, default=50)  # Giới hạn số lượt trao đổi tối đa
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)  # "draft" hoặc "active"
    kb_retrieval_mode: Mapped[str] = mapped_column(String(20), default="tool")  # "auto" hoặc "tool"

    # Quan hệ
    user: Mapped["User"] = relationship(back_populates="agents")
    tools: Mapped[list["Tool"]] = relationship(secondary="agent_tools", lazy="selectin")
    knowledge_bases: Mapped[list["KnowledgeBase"]] = relationship(
        secondary="agent_knowledge_bases", lazy="selectin"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )
    workflows: Mapped[list["Workflow"]] = relationship(back_populates="agent")
