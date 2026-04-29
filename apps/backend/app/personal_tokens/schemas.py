"""Schemas for personal access token CRUD (browser-facing)."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# ─── Scopes ─────────────────────────────────────────────────────────


# Coarse-grained scope catalogue. Keep stable — frontend renders a checkbox
# per entry. Adding a scope is non-breaking; removing/renaming is breaking
# (existing tokens may carry obsolete strings, treat as deny).
ALLOWED_SCOPES: set[str] = {
    "agents:read",
    "agents:chat",
    "conversations:read",
    "conversations:write",
    "knowledge:read",
    "workflows:read",
    "workflows:execute",
}


# ─── Request / response shapes ─────────────────────────────────────


class TokenCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=list)
    # Optional ISO datetime — null means never expire.
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: list[str]) -> list[str]:
        unknown = set(v) - ALLOWED_SCOPES
        if unknown:
            raise ValueError(f"Unknown scopes: {sorted(unknown)}")
        # Dedupe + stable order
        return sorted(set(v))


class TokenResponse(BaseModel):
    """Safe shape — never includes the plaintext key."""

    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenCreatedResponse(TokenResponse):
    """Returned ONLY at creation time — includes the plaintext token.

    Frontend must show this to the user once and then drop it; the value
    cannot be retrieved again.
    """

    plaintext: str
