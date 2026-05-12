"""Public OIDC SSO endpoints.

  GET /api/sso/oidc/{org_slug}/login     redirect to IdP authorize URL
  GET /api/sso/oidc/{org_slug}/callback  exchange code, JIT provision,
                                         set auth cookies, redirect to FE

Per-org config lives in ``sso_configurations`` (one row per org).
First login from a new user creates the User row + WorkspaceMember
in the org's default workspace when ``jit_provisioning`` is on.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.modules.auth.router import _set_auth_cookies
from app.modules.auth.service import get_user_by_email
from app.modules.sso.oidc import (
    OIDCDiscoveryError,
    discover,
    exchange_code,
    fetch_userinfo,
    map_claims,
)
from app.modules.sso.service import get_oidc_client_secret, get_sso_config_by_org_slug
from app.platform.config import settings
from app.platform.db.session import get_db

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/sso/oidc", tags=["sso"])

_STATE_COOKIE = "oidc_state"
_STATE_TTL_SECONDS = 600  # 10 min — login flow shouldn't take longer.


# ─── State (CSRF) signing ─────────────────────────────────────────


def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="sso-oidc-state")


def _build_state(org_slug: str, redirect_to: str | None) -> tuple[str, str]:
    """Return (nonce, signed_cookie_payload)."""
    nonce = secrets.token_urlsafe(24)
    return nonce, _signer().dumps(
        {"nonce": nonce, "org": org_slug, "rt": _safe_redirect(redirect_to)}
    )


def _consume_state(signed: str | None, *, org_slug: str, nonce: str) -> str:
    if not signed:
        raise HTTPException(400, detail="Missing SSO state")
    try:
        payload = _signer().loads(signed, max_age=_STATE_TTL_SECONDS)
    except SignatureExpired:
        raise HTTPException(400, detail="SSO state expired")
    except BadSignature:
        raise HTTPException(400, detail="Invalid SSO state")
    if payload.get("org") != org_slug or payload.get("nonce") != nonce:
        raise HTTPException(400, detail="SSO state mismatch")
    return _safe_redirect(payload.get("rt"))


def _safe_redirect(target: str | None) -> str:
    """Only allow same-origin paths — defends against open redirect."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return "/home"
    return target


def _frontend_url(path: str = "") -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}{path}" if path.startswith("/") or not path else base


def _redirect_uri(request: Request, org_slug: str) -> str:
    """Compute the absolute callback URL. Honours forwarded proto so
    HTTPS proxies (cloudflare, nginx) work without env override."""
    host = request.headers.get("x-forwarded-host") or request.url.netloc
    scheme = request.headers.get("x-forwarded-proto") or request.url.scheme
    return f"{scheme}://{host}{settings.API_PREFIX}/sso/oidc/{org_slug}/callback"


# ─── /login ───────────────────────────────────────────────────────


@router.get("/{org_slug}/login")
async def oidc_login(
    org_slug: str,
    request: Request,
    redirect_to: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Kick off the OIDC handshake for ``org_slug``."""
    config = await get_sso_config_by_org_slug(db, org_slug, provider="oidc")
    if config is None or not config.oidc_issuer or not config.oidc_client_id:
        raise HTTPException(404, detail="OIDC not configured for this org")

    try:
        discovery = await discover(config.oidc_issuer)
    except OIDCDiscoveryError as exc:
        logger.exception("OIDC discovery failed for org=%s", org_slug)
        raise HTTPException(503, detail=str(exc))

    nonce, signed_state = _build_state(org_slug, redirect_to)

    params = {
        "client_id": config.oidc_client_id,
        "redirect_uri": _redirect_uri(request, org_slug),
        "response_type": "code",
        "scope": " ".join(config.oidc_scopes or ["openid", "email", "profile"]),
        "state": nonce,
    }
    authorize_url = f"{discovery['authorization_endpoint']}?{urlencode(params)}"

    resp = RedirectResponse(url=authorize_url, status_code=302)
    resp.set_cookie(
        key=_STATE_COOKIE,
        value=signed_state,
        max_age=_STATE_TTL_SECONDS,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path=f"{settings.API_PREFIX}/sso/oidc",
    )
    return resp


# ─── /callback ────────────────────────────────────────────────────


@router.get("/{org_slug}/callback")
async def oidc_callback(
    org_slug: str,
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Handle the IdP redirect. Always returns 302 — never raw error
    bodies, since the user is in their browser tab from the IdP."""
    fail_url = _frontend_url("/login?error=sso_failed")

    if error or not code or not state:
        logger.warning("OIDC callback missing fields or carrying error: %s", error)
        return _fail(fail_url)

    try:
        redirect_to = _consume_state(
            request.cookies.get(_STATE_COOKIE), org_slug=org_slug, nonce=state
        )
    except HTTPException as exc:
        logger.warning("OIDC state rejected: %s", exc.detail)
        return _fail(fail_url)

    config = await get_sso_config_by_org_slug(db, org_slug, provider="oidc")
    if config is None or not config.oidc_issuer or not config.oidc_client_id:
        return _fail(fail_url)
    client_secret = get_oidc_client_secret(config)
    if not client_secret:
        logger.error("OIDC config for org=%s has no client_secret", org_slug)
        return _fail(fail_url)

    try:
        discovery = await discover(config.oidc_issuer)
        token = await exchange_code(
            token_endpoint=discovery["token_endpoint"],
            code=code,
            redirect_uri=_redirect_uri(request, org_slug),
            client_id=config.oidc_client_id,
            client_secret=client_secret,
        )
        access_token = token.get("access_token")
        if not access_token:
            return _fail(fail_url)
        userinfo = await fetch_userinfo(
            userinfo_endpoint=discovery["userinfo_endpoint"],
            access_token=access_token,
        )
    except OIDCDiscoveryError as exc:
        logger.warning("OIDC exchange/userinfo failed for org=%s: %s", org_slug, exc)
        return _fail(fail_url)

    claims = map_claims(userinfo, config.attribute_mapping or {})
    if not claims["email"]:
        logger.warning("OIDC userinfo missing email for org=%s", org_slug)
        return _fail(_frontend_url("/login?error=sso_no_email"))

    user = await _match_or_provision_user(db, config.organization_id, config, claims)
    if user is None:
        # Email exists on platform but not verified by another flow —
        # bail out, ask user to log in with password first.
        return _fail(_frontend_url("/login?error=sso_email_exists"))

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    resp = RedirectResponse(
        url=_frontend_url(redirect_to), status_code=status.HTTP_302_FOUND
    )
    resp.delete_cookie(_STATE_COOKIE, path=f"{settings.API_PREFIX}/sso/oidc")
    _set_auth_cookies(
        resp,
        str(user.id),
        token_version=user.token_version,
        remember=True,
    )
    return resp


def _fail(url: str) -> RedirectResponse:
    resp = RedirectResponse(url=url, status_code=302)
    resp.delete_cookie(_STATE_COOKIE, path=f"{settings.API_PREFIX}/sso/oidc")
    return resp


# ─── User matching / JIT provisioning ─────────────────────────────


async def _match_or_provision_user(
    db: AsyncSession,
    organization_id,
    config,
    claims: dict,
) -> User | None:
    """Find or create a User for this OIDC login.

    Order:
      1. Match by email (verified → reuse + add WorkspaceMember if absent).
      2. No match + JIT enabled → create User + personal workspace
         + WorkspaceMember in the SSO org's default workspace.
      3. No match + JIT disabled → 404 (admin must invite first).
    """
    email = claims["email"].lower().strip()
    existing = await get_user_by_email(db, email)

    if existing is not None:
        if not claims["email_verified"]:
            # Don't auto-link unverified email — same guard as OAuth.
            return None
        # Ensure they're a member of the SSO org's default workspace.
        await _ensure_workspace_member(
            db, existing.id, organization_id, config.default_role
        )
        if not existing.is_verified:
            existing.is_verified = True
            existing.verified_at = datetime.now(timezone.utc)
        return existing

    if not config.jit_provisioning:
        # Admin policy: only invited users can land via SSO.
        return None

    # Fresh provision: user row + personal workspace (via signup helper)
    # + membership in the SSO org's default workspace.
    user = User(
        email=email,
        hashed_password=None,
        full_name=claims.get("full_name"),
        is_active=True,
        is_verified=True,
        verified_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    # Personal workspace so the user always has somewhere to land —
    # matches OAuth/email-signup behaviour.
    from app.modules.workspaces.service import ensure_personal_workspace

    await ensure_personal_workspace(db, user)

    await _ensure_workspace_member(db, user.id, organization_id, config.default_role)
    return user


async def _ensure_workspace_member(
    db: AsyncSession,
    user_id,
    organization_id,
    role: str,
) -> None:
    """Idempotently add the user to the SSO org's default workspace.

    "Default" = the first non-personal workspace under the org (most
    orgs have exactly one). If no workspace exists yet we silently
    skip — admin can move them via the UI.
    """
    ws = await db.scalar(
        select(Workspace)
        .where(Workspace.organization_id == organization_id, Workspace.is_personal.is_(False))
        .order_by(Workspace.created_at)
    )
    if ws is None:
        return

    existing = await db.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if existing is not None:
        return

    db.add(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=user_id,
            role=role,
        )
    )
    await db.flush()
