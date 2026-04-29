"""OAuth Authorization-Code flow for GitHub + Google.

State (CSRF token) + optional ``redirect_to`` are stored in a short-lived
signed cookie — not in a server-side session store — so the backend stays
stateless.
"""

from __future__ import annotations

import json
import logging
import secrets
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import settings
from app.models.oauth_account import PROVIDER_GITHUB, PROVIDER_GOOGLE

logger = logging.getLogger("agentforge")

STATE_COOKIE = "oauth_state"
STATE_TTL_SECONDS = 5 * 60  # 5 minutes


@dataclass(frozen=True)
class ProviderConfig:
    key: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str
    client_id: str
    client_secret: str

    @property
    def enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)


@dataclass(frozen=True)
class ProviderProfile:
    """Normalised subset of the provider's userinfo response."""

    provider: str
    provider_user_id: str
    email: str
    email_verified: bool
    full_name: str | None


# ─── Provider registry ──────────────────────────────────────────────

def _providers() -> dict[str, ProviderConfig]:
    return {
        PROVIDER_GITHUB: ProviderConfig(
            key=PROVIDER_GITHUB,
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scope="read:user user:email",
            client_id=settings.GITHUB_CLIENT_ID,
            client_secret=settings.GITHUB_CLIENT_SECRET,
        ),
        PROVIDER_GOOGLE: ProviderConfig(
            key=PROVIDER_GOOGLE,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scope="openid email profile",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
        ),
    }


def get_provider(key: str) -> ProviderConfig:
    providers = _providers()
    config = providers.get(key)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown OAuth provider: {key}",
        )
    if not config.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth provider '{key}' is not configured",
        )
    return config


# ─── State cookie helpers ───────────────────────────────────────────

def _signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.SECRET_KEY, salt="oauth-state")


def build_state(provider: str, redirect_to: str | None) -> tuple[str, str]:
    """Return (nonce, signed_cookie_value)."""
    nonce = secrets.token_urlsafe(24)
    payload = {
        "nonce": nonce,
        "provider": provider,
        "redirect_to": _safe_redirect(redirect_to),
    }
    cookie_value = _signer().dumps(payload)
    return nonce, cookie_value


def consume_state(
    signed_cookie: str | None,
    provider: str,
    received_nonce: str,
) -> str:
    """Verify the signed state cookie against the nonce received in the
    callback, and return the safe redirect target."""
    if not signed_cookie:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth state",
        )
    try:
        payload = _signer().loads(signed_cookie, max_age=STATE_TTL_SECONDS)
    except SignatureExpired:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state expired",
        )
    except BadSignature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    if payload.get("provider") != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state provider mismatch",
        )
    if payload.get("nonce") != received_nonce:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state nonce mismatch",
        )

    return _safe_redirect(payload.get("redirect_to"))


def _safe_redirect(redirect_to: str | None) -> str:
    """Only accept same-origin paths — block open redirects like ``//evil.com``."""
    if not redirect_to:
        return "/"
    if not redirect_to.startswith("/") or redirect_to.startswith("//"):
        return "/"
    return redirect_to


# ─── Provider-specific network calls ────────────────────────────────

async def exchange_code_for_token(
    config: ProviderConfig,
    code: str,
    redirect_uri: str,
) -> str:
    """Exchange an auth code for an access token. Returns the access token."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
    }
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(config.token_url, data=data, headers=headers)

    if resp.status_code >= 400:
        logger.error(
            "OAuth token exchange failed [%s]: %s %s",
            config.key,
            resp.status_code,
            resp.text[:500],
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth token exchange failed",
        )

    try:
        payload = resp.json()
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth provider returned non-JSON",
        )

    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth response missing access_token: {payload.get('error', 'unknown')}",
        )
    return access_token


async def fetch_profile(
    config: ProviderConfig,
    access_token: str,
) -> ProviderProfile:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(config.userinfo_url, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch OAuth profile",
            )
        data = resp.json()

        # GitHub hides emails when user sets them private — need a second call
        if config.key == PROVIDER_GITHUB and not data.get("email"):
            emails_resp = await client.get(
                "https://api.github.com/user/emails", headers=headers
            )
            if emails_resp.status_code == 200:
                for row in emails_resp.json():
                    if row.get("primary") and row.get("verified"):
                        data["email"] = row["email"]
                        data["_email_verified"] = True
                        break

    return _normalise_profile(config.key, data)


def _normalise_profile(provider: str, data: dict) -> ProviderProfile:
    if provider == PROVIDER_GITHUB:
        email = data.get("email") or ""
        return ProviderProfile(
            provider=PROVIDER_GITHUB,
            provider_user_id=str(data["id"]),
            email=email,
            # GitHub's /user endpoint doesn't carry a verified flag, but the
            # /user/emails endpoint does — honoured above via `_email_verified`.
            email_verified=bool(data.get("_email_verified", False)) or bool(email),
            full_name=data.get("name") or data.get("login"),
        )

    if provider == PROVIDER_GOOGLE:
        return ProviderProfile(
            provider=PROVIDER_GOOGLE,
            provider_user_id=str(data["sub"]),
            email=data.get("email") or "",
            email_verified=bool(data.get("email_verified", False)),
            full_name=data.get("name"),
        )

    raise ValueError(f"Unknown provider {provider}")


# ─── Redirect URI (computed, not stored) ────────────────────────────

def redirect_uri_for(request: Request, provider: str) -> str:
    """Build the callback URL the provider should redirect to.

    We derive from the incoming ``request.base_url`` so local / staging /
    production all Just Work without per-env config.
    """
    base = str(request.base_url).rstrip("/")
    return f"{base}{settings.API_PREFIX}/auth/oauth/{provider}/callback"
