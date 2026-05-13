"""Private helpers shared across the auth subrouters.

Lives at the module root (not under ``routers/``) so non-router code
that also needs a cookie helper or a rate-limit constant can import
without reaching into a sibling subrouter file.
"""

from __future__ import annotations

from fastapi import Depends, Response

from app.modules.identity.auth.service import (
    create_access_token,
    create_refresh_token,
)
from app.platform.config import settings
from app.platform.rate_limit import make_limit

# Public auth endpoints (no session yet) are the most-attacked surface —
# strict per-IP limits so credential-stuffing costs the attacker.
AUTH_PUBLIC_LIMIT = Depends(make_limit("auth-public", 30))
# Authenticated endpoints get more headroom via per-user keys.
AUTH_USER_LIMIT = Depends(make_limit("auth-user", 60))


def set_auth_cookies(
    response: Response,
    user_id: str,
    *,
    token_version: int = 0,
    remember: bool = False,
) -> None:
    """Gán access_token + refresh_token vào HTTP-only cookie.

    * access_token cookie: path=/, TTL từ ACCESS_TOKEN_EXPIRE_MINUTES
    * refresh_token cookie: path=/api/auth/refresh, TTL phụ thuộc ``remember``
    """
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id, token_version, remember=remember)

    refresh_days = (
        settings.REMEMBER_ME_EXPIRE_DAYS
        if remember
        else settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=refresh_days * 86400,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path=f"{settings.API_PREFIX}/auth/refresh",
    )
