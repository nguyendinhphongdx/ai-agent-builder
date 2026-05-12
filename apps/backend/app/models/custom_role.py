"""Org-defined permission set. The ``slug`` lives in
``workspace_members.role`` exactly like a built-in role string —
the resolver checks built-ins first, falls back to this table."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base, TimestampMixin, UUIDMixin


class CustomRole(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "custom_roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_custom_roles_org_slug"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # URL-safe identifier. Stored in workspace_members.role for members
    # carrying this role. UNIQUE per org so the lookup is unambiguous.
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Array of permission strings from app.platform.permissions.catalogue.
    # Service layer rejects unknown permission names before insert,
    # so consumers can trust the contents.
    permissions: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )
