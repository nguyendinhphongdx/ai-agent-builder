"""Discord inbound trigger.

Discord interactions are signed with Ed25519. The bot's
``discord_public_key`` is required to verify; it is not a secret
(Discord shows it in the developer portal alongside the
application id) so we store it as plaintext.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base, TimestampMixin, UUIDMixin


class DiscordTrigger(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "discord_triggers"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discord_application_id: Mapped[str] = mapped_column(String(64), nullable=False)
    discord_public_key: Mapped[str] = mapped_column(String(128), nullable=False)
    filter_command: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    workflow: Mapped["Workflow"] = relationship()
