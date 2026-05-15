"""OAuth endpoints — delegates provider I/O to ``app.modules.identity.auth.oauth``."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_account import OAuthAccount
from app.models.user import User
from app.modules.identity.auth._internal import set_auth_cookies
from app.modules.identity.auth.oauth import (
    STATE_COOKIE,
    STATE_TTL_SECONDS,
    build_state,
    consume_state,
    exchange_code_for_token,
    fetch_profile,
    get_provider,
    redirect_uri_for,
)
from app.modules.identity.auth.service import get_user_by_email
from app.platform.config import settings
from app.platform.db.session import get_db

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/auth/oauth", tags=["auth"])


def _frontend_url(path: str = "") -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    if not path:
        return base
    return f"{base}{path if path.startswith('/') else '/' + path}"


# ─── Start ─────────────────────────────────────────────────────────

@router.get("/{provider}/start")
async def oauth_start(
    provider: str,
    request: Request,
    redirect_to: str | None = Query(default=None),
):
    """Redirect the browser to the provider's consent screen."""
    config = get_provider(provider)
    nonce, signed_state = build_state(provider, redirect_to)

    params = {
        "client_id": config.client_id,
        "redirect_uri": redirect_uri_for(request, provider),
        "scope": config.scope,
        "state": nonce,
        "response_type": "code",
    }
    # Google needs prompt=consent to always get refresh_token (if ever needed)
    if provider == "google":
        params["access_type"] = "online"

    authorize_url = f"{config.authorize_url}?{urlencode(params)}"

    response = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=STATE_COOKIE,
        value=signed_state,
        max_age=STATE_TTL_SECONDS,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path=f"{settings.API_PREFIX}/auth/oauth",
    )
    return response


# ─── Callback ──────────────────────────────────────────────────────

@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Handle provider redirect. Always returns a 302 back to the frontend."""
    failure_url = _frontend_url("/login?error=oauth_failed")

    if error or not code or not state:
        logger.warning("OAuth callback missing fields or carrying error: %s", error)
        return _fail(failure_url)

    # Verify state (burns the cookie)
    try:
        redirect_to = consume_state(
            request.cookies.get(STATE_COOKIE),
            provider=provider,
            received_nonce=state,
        )
    except HTTPException as e:
        logger.warning("OAuth state rejected: %s", e.detail)
        return _fail(failure_url)

    # Exchange + profile
    try:
        config = get_provider(provider)
        access_token = await exchange_code_for_token(
            config,
            code=code,
            redirect_uri=redirect_uri_for(request, provider),
        )
        profile = await fetch_profile(config, access_token)
    except HTTPException as e:
        logger.warning("OAuth exchange/profile failed: %s", e.detail)
        return _fail(failure_url)

    if not profile.email:
        logger.warning("OAuth profile missing email for %s", provider)
        return _fail(_frontend_url("/login?error=oauth_no_email"))

    # Match / link / create user
    user = await _match_or_create_user(db, profile)
    if user is None:
        # Email collision without verified-link permission — tell user to
        # sign in with password first so they can link afterwards.
        return _fail(_frontend_url("/login?error=oauth_email_exists"))

    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    # Success → land the user on the intended page with cookies set
    resp = RedirectResponse(
        url=_frontend_url(redirect_to),
        status_code=status.HTTP_302_FOUND,
    )
    # Clear state cookie
    resp.delete_cookie(STATE_COOKIE, path=f"{settings.API_PREFIX}/auth/oauth")
    set_auth_cookies(
        resp,
        str(user.id),
        token_version=user.token_version,
        remember=True,  # OAuth sign-ins get the 30d session
    )
    return resp


def _fail(url: str) -> RedirectResponse:
    resp = RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(STATE_COOKIE, path=f"{settings.API_PREFIX}/auth/oauth")
    return resp


# ─── Matching logic ────────────────────────────────────────────────

async def _match_or_create_user(db: AsyncSession, profile) -> User | None:
    # 1) Already linked?
    result = await db.execute(
        select(OAuthAccount).where(
            OAuthAccount.provider == profile.provider,
            OAuthAccount.provider_user_id == profile.provider_user_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is not None:
        # Refresh recorded email if provider changed it
        if account.provider_email != profile.email:
            account.provider_email = profile.email
        return await _load_user(db, account.user_id)

    # 2) Email collision — only auto-link if provider verified the email
    existing = await get_user_by_email(db, profile.email)
    if existing is not None:
        if not profile.email_verified:
            return None  # do not auto-link unverified email
        db.add(
            OAuthAccount(
                user_id=existing.id,
                provider=profile.provider,
                provider_user_id=profile.provider_user_id,
                provider_email=profile.email,
            )
        )
        if not existing.is_verified:
            existing.is_verified = True
            existing.verified_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    # 3) Fresh signup — create user + link
    user = User(
        email=profile.email,
        hashed_password=None,
        full_name=profile.full_name,
        is_active=True,
        is_verified=bool(profile.email_verified),
        verified_at=datetime.now(timezone.utc) if profile.email_verified else None,
    )
    db.add(user)
    await db.flush()
    db.add(
        OAuthAccount(
            user_id=user.id,
            provider=profile.provider,
            provider_user_id=profile.provider_user_id,
            provider_email=profile.email,
        )
    )
    await db.flush()
    # Same provisioning the password-signup path gets — see
    # ``auth.service.create_user``. Has to run after the user row
    # exists so the workspace owner FK has something to point at.
    from app.modules.identity.workspaces.service import ensure_personal_workspace
    await ensure_personal_workspace(db, user)
    return user


async def _load_user(db: AsyncSession, user_id) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
