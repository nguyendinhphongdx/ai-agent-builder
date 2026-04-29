"""Agent Hub — published agents that other users can browse and fork."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentTemplate(Base):
    """Published agent — available in the Hub for browse + fork.

    The author (``user_id``) is the DB owner — only they can edit/unpublish.
    ``author_name`` is free-text shown in the UI; defaults to the user's
    display name but can be overridden (e.g. brand name like "AgentForge").
    """

    __tablename__ = "agent_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=__import__("sqlalchemy").text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Source agent the template was published from. Nullable because the
    # author may delete the working agent later — the template stays alive
    # via the frozen snapshot stored on each version row.
    source_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    cover_image_url: Mapped[str | None] = mapped_column(Text)

    price_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # draft | published | suspended | archived
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    # When true, publishing this template clones author's KB documents +
    # chunks (content + embedding) into a frozen per-version dataset so
    # buyers fork with the knowledge content already loaded. Must be
    # accompanied by an "I understand this is permanent" consent at the
    # publish step — see `hub.service.publish_agent`.
    include_kb_content: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Aggregates — denormalised, refreshed on fork / review write.
    fork_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_avg: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))

    # Relationships
    author: Mapped["User"] = relationship()
    versions: Mapped[list["AgentTemplateVersion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="AgentTemplateVersion.created_at.desc()",
    )
