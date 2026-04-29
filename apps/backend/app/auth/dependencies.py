"""Auth dependencies — resolve current user from cookie OR API token header.

Single ``get_current_user`` accepts both:
  - ``Authorization: Bearer afpt_...`` header (external API clients)
  - ``access_token`` cookie (browser sessions)

Header takes precedence when both are present. The resolved
:class:`PersonalAccessToken` is stashed on ``request.state.api_token`` so
downstream dependencies (``require_scope``, rate-limit middleware) can
distinguish API requests from cookie requests without re-decoding.
"""
from __future__ import annotations

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import decode_token, get_user_by_id
from app.context import set_current_user_id
from app.db.session import get_db
from app.models.user import User
from app.personal_tokens.service import verify_plaintext


def _bearer_token(authorization: str | None) -> str | None:
    """Extract the token portion of an ``Authorization: Bearer <value>`` header."""
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def get_current_user(
    request: Request,
    access_token: str | None = Cookie(default=None),
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current user from API token (header) or cookie session."""
    # ── 1. Bearer API token ──────────────────────────────────────────
    bearer = _bearer_token(authorization)
    if bearer:
        result = await verify_plaintext(db, bearer)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked API token",
            )
        token, user = result
        # Stash for require_scope + rate-limit middleware downstream.
        request.state.api_token = token
        set_current_user_id(user.id)
        return user

    # ── 2. Cookie session ────────────────────────────────────────────
    request.state.api_token = None  # explicit: marker for "not API auth"

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    payload = decode_token(access_token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    set_current_user_id(user.id)
    return user


def require_scope(scope: str):
    """Dependency factory — enforce a scope when the request is API-key auth.

    Cookie sessions bypass scope checks entirely: a logged-in browser session
    is the resource owner with full permission. API tokens are explicitly
    constrained — token must list ``scope`` in its ``scopes`` array.

    Note: callers must declare ``Depends(get_current_user)`` BEFORE this
    dependency in the endpoint signature so ``request.state.api_token`` is set.
    """

    async def _check(request: Request) -> None:
        token = getattr(request.state, "api_token", None)
        if token is None:
            return  # cookie session — owner, allow
        if scope not in (token.scopes or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Token missing required scope: {scope}",
            )

    return _check
