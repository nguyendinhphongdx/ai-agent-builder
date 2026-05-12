"""OAuth dance: start → callback → token storage → refresh.

The router stays thin; this module owns the state-token lifecycle
and the encrypted-token plumbing.

Public surface for callers:
  - start_oauth(provider_id, return_to)        → authorize URL
  - complete_oauth(provider_id, code, state)   → OAuthConnection
  - list_connections()                          → workspace's connections
  - delete_connection(connection_id)            → remove
  - get_access_token(connection_id)             → current bearer token,
                                                  refreshing in-place
                                                  when expired
"""
from __future__ import annotations

import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.oauth_connection import OAuthConnection, OAuthState
from app.modules.oauth_connectors.providers import (
    OAuthProvider,
    ParsedToken,
    get_provider,
)
from app.platform.config import settings
from app.platform.context import current_user_id, current_workspace_id_or_none
from app.platform.security.crypto import decrypt_secret, encrypt_secret

logger = logging.getLogger("agentforge")

_STATE_TTL_MINUTES = 10
_REFRESH_SKEW_SECONDS = 60  # refresh slightly before real expiry


def _redirect_uri(provider_id: str) -> str:
    base = settings.OAUTH_REDIRECT_BASE_URL.rstrip("/")
    return f"{base}{settings.API_PREFIX}/oauth-connectors/{provider_id}/callback"


# ─── start ─────────────────────────────────────────────────────────


async def start_oauth(
    db: AsyncSession,
    *,
    provider_id: str,
    return_to: str | None = None,
) -> str:
    """Mint a state token + return the provider authorize URL."""
    provider = get_provider(provider_id)
    if provider is None:
        raise ValueError(f"unknown OAuth provider: {provider_id}")
    if not provider.is_configured():
        raise ValueError(
            f"{provider.label} OAuth is not configured on this deployment"
        )

    workspace_id = current_workspace_id_or_none()
    user_id = current_user_id()
    if workspace_id is None:
        raise ValueError("no active workspace")

    state = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    db.add(
        OAuthState(
            state=state,
            workspace_id=workspace_id,
            user_id=user_id,
            provider=provider_id,
            return_to=return_to,
            created_at=now,
            expires_at=now + timedelta(minutes=_STATE_TTL_MINUTES),
        )
    )
    await db.flush()

    params: dict[str, str] = {
        "client_id": provider.client_id(),
        "redirect_uri": _redirect_uri(provider_id),
        "response_type": "code",
        "state": state,
    }
    if provider.default_scope:
        params["scope"] = provider.default_scope
    if provider.extra_authorize_params:
        params.update(provider.extra_authorize_params)

    return f"{provider.authorize_url}?{urlencode(params)}"


# ─── callback ──────────────────────────────────────────────────────


async def _consume_state(db: AsyncSession, state: str) -> OAuthState:
    row = await db.scalar(
        select(OAuthState).where(OAuthState.state == state)
    )
    if row is None:
        raise ValueError("unknown state token (already used or expired)")
    if row.expires_at < datetime.now(timezone.utc):
        await db.delete(row)
        raise ValueError("state token expired")
    # Single-use — delete after first read.
    await db.delete(row)
    return row


async def _exchange_code(
    provider: OAuthProvider, code: str
) -> dict[str, Any]:
    """Exchange the auth code for token JSON. Provider-specific
    auth style picks between Basic header vs. form-encoded client
    credentials in the body."""
    redirect_uri = _redirect_uri(provider.id)
    form: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }
    headers = {"Accept": "application/json"}

    if provider.token_auth_style == "form":
        form["client_id"] = provider.client_id()
        form["client_secret"] = provider.client_secret()
        auth = None
    else:
        auth = (provider.client_id(), provider.client_secret())

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            provider.token_url,
            data=form,
            headers=headers,
            auth=auth,
        )
        # Slack returns 200 with ok=false on error; the parser
        # handles that. Other providers return non-2xx.
        if resp.status_code >= 400:
            raise ValueError(
                f"{provider.id} token exchange failed: "
                f"{resp.status_code} {resp.text[:300]}"
            )
        return resp.json()


async def complete_oauth(
    db: AsyncSession, *, provider_id: str, code: str, state: str
) -> tuple[OAuthConnection, str | None]:
    """Finish the dance: validate state, exchange code, upsert
    connection row. Returns (connection, return_to_url)."""
    provider = get_provider(provider_id)
    if provider is None:
        raise ValueError(f"unknown OAuth provider: {provider_id}")

    state_row = await _consume_state(db, state)
    if state_row.provider != provider_id:
        raise ValueError("state/provider mismatch")

    token_data = await _exchange_code(provider, code)
    parsed: ParsedToken = provider.parse(token_data)

    expires_at = None
    if parsed.expires_in:
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(parsed.expires_in)
        )

    # Upsert by (workspace, provider, external_account_id). Re-
    # connecting the same Slack workspace overwrites in place.
    row = await db.scalar(
        select(OAuthConnection).where(
            OAuthConnection.workspace_id == state_row.workspace_id,
            OAuthConnection.provider == provider_id,
            OAuthConnection.external_account_id == parsed.external_account_id,
        )
    )
    if row is None:
        row = OAuthConnection(
            workspace_id=state_row.workspace_id,
            user_id=state_row.user_id,
            provider=provider_id,
            account_label=parsed.account_label,
            external_account_id=parsed.external_account_id,
            access_token_enc=encrypt_secret(parsed.access_token),
            refresh_token_enc=(
                encrypt_secret(parsed.refresh_token)
                if parsed.refresh_token
                else None
            ),
            expires_at=expires_at,
            scope=parsed.scope,
            raw_response=parsed.raw,
        )
        db.add(row)
    else:
        row.access_token_enc = encrypt_secret(parsed.access_token)
        if parsed.refresh_token:
            row.refresh_token_enc = encrypt_secret(parsed.refresh_token)
        row.expires_at = expires_at
        row.scope = parsed.scope
        row.account_label = parsed.account_label or row.account_label
        row.raw_response = parsed.raw

    await db.flush()
    return row, state_row.return_to


# ─── reads ─────────────────────────────────────────────────────────


async def list_connections(db: AsyncSession) -> Sequence[OAuthConnection]:
    workspace_id = current_workspace_id_or_none()
    stmt = select(OAuthConnection).order_by(OAuthConnection.created_at.desc())
    if workspace_id is not None:
        stmt = stmt.where(OAuthConnection.workspace_id == workspace_id)
    return (await db.execute(stmt)).scalars().all()


async def get_connection(
    db: AsyncSession, connection_id: uuid.UUID
) -> OAuthConnection | None:
    workspace_id = current_workspace_id_or_none()
    stmt = select(OAuthConnection).where(OAuthConnection.id == connection_id)
    if workspace_id is not None:
        stmt = stmt.where(OAuthConnection.workspace_id == workspace_id)
    return await db.scalar(stmt)


async def delete_connection(
    db: AsyncSession, connection: OAuthConnection
) -> None:
    await db.delete(connection)
    await db.flush()


# ─── token helpers (refresh) ───────────────────────────────────────


async def _refresh_access_token(
    db: AsyncSession, connection: OAuthConnection, provider: OAuthProvider
) -> str:
    """Use the stored refresh token to mint a fresh access token.
    Persists the new access (and refresh, when the provider
    rotates it). Returns the new plaintext access token."""
    if not connection.refresh_token_enc:
        raise ValueError(
            f"connection {connection.id} has no refresh token; reconnect required"
        )
    refresh_token = decrypt_secret(connection.refresh_token_enc)

    form = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    if provider.token_auth_style == "form":
        form["client_id"] = provider.client_id()
        form["client_secret"] = provider.client_secret()
        auth = None
    else:
        auth = (provider.client_id(), provider.client_secret())

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            provider.token_url,
            data=form,
            headers={"Accept": "application/json"},
            auth=auth,
        )
        if resp.status_code >= 400:
            raise ValueError(
                f"{provider.id} refresh failed: {resp.status_code} {resp.text[:300]}"
            )
        data = resp.json()

    parsed = provider.parse(data)
    connection.access_token_enc = encrypt_secret(parsed.access_token)
    if parsed.refresh_token:
        # Some providers rotate refresh tokens — persist the new one.
        connection.refresh_token_enc = encrypt_secret(parsed.refresh_token)
    if parsed.expires_in:
        connection.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(parsed.expires_in)
        )
    else:
        connection.expires_at = None
    await db.flush()
    return parsed.access_token


async def get_access_token(
    db: AsyncSession, connection_id: uuid.UUID
) -> str:
    """Return a valid bearer token for the connection. Refreshes
    transparently when the stored access token is within
    ``_REFRESH_SKEW_SECONDS`` of expiry.

    Used by connector providers — they pass the connection id and
    get a plaintext token they can put in ``Authorization: Bearer``.
    """
    connection = await get_connection(db, connection_id)
    if connection is None:
        raise ValueError(f"oauth connection {connection_id} not found")
    provider = get_provider(connection.provider)
    if provider is None:
        raise ValueError(f"oauth provider {connection.provider} not registered")

    needs_refresh = (
        connection.expires_at is not None
        and connection.expires_at
        <= datetime.now(timezone.utc)
        + timedelta(seconds=_REFRESH_SKEW_SECONDS)
    )
    if needs_refresh:
        try:
            return await _refresh_access_token(db, connection, provider)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "oauth refresh failed for %s/%s: %s",
                connection.provider,
                connection.id,
                exc,
            )
            # Surface the error to the caller — connector will
            # mark itself errored and the FE can prompt re-connect.
            raise

    return decrypt_secret(connection.access_token_enc)


__all__ = [
    "start_oauth",
    "complete_oauth",
    "list_connections",
    "get_connection",
    "delete_connection",
    "get_access_token",
]


# ``json`` is imported but only used implicitly via httpx; placate
# unused-import linting in case ruff disagrees.
_ = json
