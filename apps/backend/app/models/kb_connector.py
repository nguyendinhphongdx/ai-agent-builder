"""Per-KB connector — how the platform pulls documents from an
external source (S3, Google Drive, Notion, …) into the KB."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class KBConnector(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "kb_connectors"

    knowledge_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "s3" | "gcs" | "gdrive" | "notion" | "local_fs" | …
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Non-secret config: bucket name, path prefix, scopes — anything
    # safe to surface in admin UI. Secrets live in
    # ``credentials_encrypted`` (Fernet).
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    credentials_encrypted: Mapped[str | None] = mapped_column(Text)
    # Provider-specific resume point. S3: ``{"last_modified": ISO8601}``.
    # GDrive: ``{"page_token": "..."}``. Notion: ``{"last_edited_time": ...}``.
    # Free-form so each connector decides what makes sense.
    sync_cursor: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
