"""Workspace — isolation boundary for resources within an organization.

Every agent / tool / knowledge base / workflow / conversation belongs
to exactly one workspace. Queries that don't filter by ``workspace_id``
are a tenancy bug — services must read the current workspace from
``app.context.current_workspace_id()`` and scope every SELECT.

A user can be a member of many workspaces (across organizations).
Membership + role lives in :class:`WorkspaceMember`.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class Workspace(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workspaces"
    __table_args__ = (
        # Slugs are unique per-org, not globally — two orgs can both have
        # a workspace called "engineering".
        UniqueConstraint("organization_id", "slug", name="uq_workspace_org_slug"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    # True for the auto-created workspace under a personal-account org.
    # Lets the UI hide team-management features and the billing layer
    # treat it specially (e.g. always Free plan, capped resources).
    is_personal: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    # Workspace-level overrides on top of org settings (theme, default
    # role for invitees, feature flags…).
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    # Enforce MFA on every login to this workspace. When true, users
    # without ``mfa_enabled=True`` are blocked at the auth dep with
    # a 403 + "must enrol MFA" detail — UI redirects to the setup page.
    force_mfa: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="workspaces")
    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    invitations: Mapped[list["WorkspaceInvitation"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
