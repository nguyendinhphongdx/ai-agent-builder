"""SCIM bearer-token authentication dependency.

IdPs (Okta, OneLogin, Azure AD) call ``/api/scim/v2/*`` with an
``Authorization: Bearer afsc_…`` header issued via the admin panel.
Resolves the token, attaches the org to ``request.state``, and
exposes it to handlers as ``scim_org_id``.

This is intentionally separate from cookie/PAT auth in
``app.modules.identity.auth.dependencies`` — SCIM has no concept of user sessions
and shouldn't surface user-facing 401 messages.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.auth.sso.service import verify_scim_token
from app.platform.db.session import get_db


def _bearer_token(authorization: str | None) -> str | None:
    """Extract token from ``Authorization: Bearer <value>``."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def require_scim_token(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """Resolve the SCIM bearer + return the organization_id.

    SCIM responses follow RFC 7644: 401 for missing/invalid creds.
    """
    bearer = _bearer_token(authorization)
    if not bearer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Missing SCIM bearer token", "status": "401"},
        )

    token = await verify_scim_token(db, bearer)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"detail": "Invalid SCIM bearer token", "status": "401"},
        )

    # Stash for handlers that need the row (e.g. audit) — kept off the
    # return shape to match the simpler "just give me the org id" pattern.
    request.state.scim_token = token
    return token.organization_id
