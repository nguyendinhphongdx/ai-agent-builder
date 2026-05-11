"""Membership of a user in a workspace, with their workspace-scoped role.

Roles form a hierarchy enforced at the permission layer:
``viewer < editor < admin < owner``. ``owner`` is the user who created
the workspace (or was promoted to take that seat); only owners can
delete the workspace or transfer ownership. Every workspace must have
at least one owner — service-layer guards enforce that invariant.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Role tier strings. Workspace-scoped — distinct from the platform role
# on User.role (user/moderator/support/admin) which governs access to
# admin tooling, not tenant resources.
WORKSPACE_ROLE_VIEWER = "viewer"
WORKSPACE_ROLE_EDITOR = "editor"
WORKSPACE_ROLE_ADMIN = "admin"
WORKSPACE_ROLE_OWNER = "owner"

WORKSPACE_ROLES = (
    WORKSPACE_ROLE_VIEWER,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_OWNER,
)


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Who sent the invite (or NULL for the auto-created owner of a
    # personal workspace). ``SET NULL`` so deleting the inviter doesn't
    # cascade-delete the member.
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="members")
    # Two FKs to users → SQLAlchemy needs `foreign_keys=` on each side
    # to disambiguate which one drives this relationship.
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    inviter: Mapped["User | None"] = relationship(foreign_keys=[invited_by])
