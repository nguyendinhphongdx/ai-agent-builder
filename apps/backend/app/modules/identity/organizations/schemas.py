"""Pydantic schemas for the organizations module."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    billing_email: str | None
    plan: str
    settings: dict
    created_at: datetime
    updated_at: datetime


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
    )
    billing_email: EmailStr | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    billing_email: EmailStr | None = None
    settings: dict | None = None


class OrgMemberResponse(BaseModel):
    """Org member row + the user it points at (small subset)."""

    user_id: uuid.UUID
    email: str
    full_name: str | None
    role: str
    invited_by: uuid.UUID | None
    joined_at: datetime


class OrgMemberInvite(BaseModel):
    """V1: invite by email of an already-existing user.

    Email-based onboarding (sending magic links to non-users) lives
    in a future ``organization_invitations`` table — out of scope for
    the initial cut.
    """

    email: EmailStr
    role: str = Field(pattern=r"^(viewer|editor|admin)$")


class OrgMemberRoleUpdate(BaseModel):
    role: str = Field(pattern=r"^(viewer|editor|admin|owner)$")
