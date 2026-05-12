"""Per-workspace CIDR allowlist. Enforced at the auth dependency
when *any* rule exists for the workspace — empty list = no restriction."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String
from sqlalchemy.dialects.postgresql import CIDR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db.base import Base, UUIDMixin


class WorkspaceIPRule(Base, UUIDMixin):
    __tablename__ = "workspace_ip_rules"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Stored as Postgres CIDR for native range comparisons. We accept
    # both /32 (single host) and broader ranges. IPv6 supported by the
    # column type out of the box.
    cidr: Mapped[str] = mapped_column(CIDR, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=False
    )
