"""Membership of a user in an organization, with their org-scoped role.

Identity at the org tier — separate from the per-workspace ACL in
``workspace_members``. The split is what makes "Acme Corp's admin
can manage every workspace inside Acme" possible without explicitly
adding them to each workspace.

Org-scoped roles mirror the workspace role names so permission
catalogues read consistently:
  ``viewer < editor < admin < owner``

Effective workspace role (computed at request time):
  * org owner  → forces workspace role ``owner`` everywhere
  * org admin  → forces workspace role ``admin`` everywhere
  * org editor → uses workspace_members.role (may be anything)
  * org viewer → clamps workspace role down to ``viewer``

That ceiling/floor rule lives in ``app.platform.permissions.roles``
— do not reimplement in handlers.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base

ORG_ROLE_VIEWER = "viewer"
ORG_ROLE_EDITOR = "editor"
ORG_ROLE_ADMIN = "admin"
ORG_ROLE_OWNER = "owner"

ORG_ROLES = (
    ORG_ROLE_VIEWER,
    ORG_ROLE_EDITOR,
    ORG_ROLE_ADMIN,
    ORG_ROLE_OWNER,
)


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # ``NULL`` for the auto-created owner of a personal organization
    # (no inviter) and for migrated legacy rows. ``SET NULL`` keeps the
    # membership row intact if the inviter is deleted later.
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # SQLAlchemy needs ``foreign_keys=`` on each side to disambiguate
    # which FK drives the relationship — same shape as WorkspaceMember.
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    inviter: Mapped["User | None"] = relationship(foreign_keys=[invited_by])
