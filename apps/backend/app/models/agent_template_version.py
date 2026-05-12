"""Frozen snapshot of an agent template at a specific release."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base


class AgentTemplateVersion(Base):
    """One release of an ``AgentTemplate``.

    ``snapshot`` is the *immutable* serialised agent + tools + KB shells
    at publish time. Forking always reads from the snapshot, never from the
    author's live agent — so seller edits don't sneak into existing forks.
    """

    __tablename__ = "agent_template_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)  # semver-ish
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    changelog: Mapped[str | None] = mapped_column(Text)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()"
    )

    template: Mapped["AgentTemplate"] = relationship(back_populates="versions")
