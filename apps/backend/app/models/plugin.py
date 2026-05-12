"""Installed-plugin registration row.

The actual *execution* of plugin code lives elsewhere (future
plugin daemon). This row is the registry source-of-truth:
"workspace X has plugin Y at version Z installed and active."
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base, TimestampMixin, UUIDMixin

PLUGIN_STATUS_ACTIVE = "active"
PLUGIN_STATUS_DISABLED = "disabled"
PLUGIN_STATUS_ERROR = "error"

PLUGIN_RUNTIME_PYTHON = "python"
PLUGIN_RUNTIME_NODEJS = "nodejs"
PLUGIN_RUNTIME_DOCKER = "docker"


class Plugin(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "plugins"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    runtime: Mapped[str] = mapped_column(String(32), nullable=False)
    manifest: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=PLUGIN_STATUS_ACTIVE
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", "version", name="uq_plugin_ws_slug_version"),
    )
