"""Pending workspace invitation.

Created when an admin invites someone by email. The recipient receives
a link containing the opaque ``token``; clicking it (while authenticated
as the invited email — or after registering with that email) accepts
the invitation, which:

  1. inserts a row in ``workspace_members`` with the offered role,
  2. stamps ``accepted_at`` here so the row becomes a historical record.

Invitations expire after ``expires_at`` and can be revoked by the inviter
before acceptance (we currently delete the row on revoke; soft-revoke
can be added later if we need an audit trail).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.db.base import Base, TimestampMixin, UUIDMixin


class WorkspaceInvitation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workspace_invitations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Role the invitee will receive on accept — must be one of the
    # WORKSPACE_ROLE_* constants in workspace_member.py. Validated at
    # the service layer (DB column stays String to keep the column
    # type stable across role-set changes).
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # Opaque random token included in the invite URL. Unique so the
    # accept endpoint can resolve invite by token alone. Plaintext
    # because it's the secret itself — rotate by deleting + reissuing.
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="invitations")
    inviter: Mapped["User | None"] = relationship()
