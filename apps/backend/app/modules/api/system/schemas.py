"""Schemas for ``/api/system/*`` — keep separate from the public
``OrganizationResponse`` so we can expose extra counters / billing
fields that customers shouldn't see on their own org payload."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SystemOrgRow(BaseModel):
    """Row in the platform-admin org table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    billing_email: str | None
    is_system: bool
    member_count: int
    workspace_count: int
    created_at: datetime


class SystemOrgDetail(SystemOrgRow):
    """Full org detail — adds settings + recent members."""

    settings: dict
    owner_email: str | None


class SystemOrgCreate(BaseModel):
    """Create an org on behalf of a customer. The platform admin assigns
    the first owner by email — that user must already exist."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=2,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$",
    )
    owner_email: EmailStr
    billing_email: EmailStr | None = None
    plan: str | None = None


class SystemOrgPatch(BaseModel):
    """Platform-admin override. Any field can be omitted to leave it."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    plan: str | None = None
    billing_email: EmailStr | None = None
    settings: dict | None = None
