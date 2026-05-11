"""Pydantic schemas for the ``/api/workspaces/*`` endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.workspace_member import (
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLE_VIEWER,
)

# Allowed roles for invites + role-change payloads. Owner is granted
# only by promoting an existing member, never via invite.
ROLE_SET_NO_OWNER = (
    WORKSPACE_ROLE_VIEWER,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_ADMIN,
)
ROLE_SET_ALL = (*ROLE_SET_NO_OWNER, WORKSPACE_ROLE_OWNER)


# ─── Workspace ─────────────────────────────────────────────────────


class OrganizationRef(BaseModel):
    """Inline org info embedded in workspace responses — saves the FE
    a separate fetch for the few fields it always wants."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str


class WorkspaceSummary(BaseModel):
    """Workspace + the *caller's* role in it. Used in the list endpoint
    so the UI can grey out actions the caller can't perform."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    is_personal: bool
    organization: OrganizationRef
    settings: dict[str, Any] = Field(default_factory=dict)
    role: str  # caller's role
    created_at: datetime


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=64)
    # Attach to an existing org; if omitted, a fresh org is spun up.
    # We don't validate membership here — the router does that after
    # resolving current_user.
    organization_id: uuid.UUID | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=64)
    settings: dict[str, Any] | None = None


# ─── Members ───────────────────────────────────────────────────────


class MemberUserRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    joined_at: datetime
    user: MemberUserRef


class MemberRoleUpdate(BaseModel):
    role: str


# ─── Invitations ───────────────────────────────────────────────────


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = Field(default=WORKSPACE_ROLE_EDITOR)


class InvitationResponse(BaseModel):
    """Sent back when an invite is created — includes the token so the
    admin can copy the accept URL manually if email delivery isn't
    wired up yet."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    email: EmailStr
    role: str
    token: str
    expires_at: datetime
    accepted_at: datetime | None = None
    created_at: datetime


class InvitationAcceptResponse(BaseModel):
    """Returned by the public accept endpoint — gives the FE enough to
    redirect into the now-joined workspace."""

    workspace: WorkspaceSummary
