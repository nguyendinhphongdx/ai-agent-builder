"""SharePoint / OneDrive KB connector via Microsoft Graph.

This single connector serves both SharePoint document libraries
and OneDrive for Business — both expose the same Drive resource
model in Microsoft Graph. Pick which drive at config time.

Auth: app-only via OAuth2 client_credentials. Admin creates an
Azure AD app, grants ``Sites.Read.All`` + ``Files.Read.All``
(application permissions, not delegated), and pastes the
tenant_id + client_id + client_secret into the credential.

Config:
  drive_id            required — target drive id (a SharePoint
                      doc library or a OneDrive root drive id).
                      Find via /sites/{site}/drives or
                      /users/{user}/drive.
  include_mime_types  optional MIME whitelist. Default: PDFs +
                      Office docs + plain/markdown.

Credentials (per-KB ai_credential row, Fernet-decrypted):
  tenant_id           Azure AD tenant id (a UUID or domain).
  client_id           App registration id.
  client_secret       App registration secret.

Incremental sync: Graph's ``/drives/{id}/root/delta`` endpoint —
the gold-standard incremental API. Returns @odata.deltaLink the
next call uses to resume; in between calls we get only the
*changes*, deletes included (rendered as "skip — file gone").
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any, AsyncIterator

import httpx

from app.knowledge.connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TOKEN_URL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
_SCOPE = "https://graph.microsoft.com/.default"
_TIMEOUT = 20.0
_LIST_BUDGET = 500

_DEFAULT_MIMES = (
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
)


_token_cache: dict[str, tuple[str, float]] = {}


async def _get_access_token(
    tenant_id: str, client_id: str, client_secret: str
) -> str:
    """Fetch (and lightly cache) an app-only access token.

    Tokens are good for 1h; we cache for ~50 minutes in-memory.
    The cache is per-process — no Redis dependency for this
    detail since refresh is cheap.
    """
    cache_key = f"{tenant_id}|{client_id}"
    now = asyncio.get_event_loop().time()
    cached = _token_cache.get(cache_key)
    if cached and cached[1] > now:
        return cached[0]

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _TOKEN_URL.format(tenant=tenant_id),
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": _SCOPE,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        token = payload["access_token"]
        # Cache for slightly less than the issued lifetime to avoid
        # racing the expiry boundary.
        expires_in = int(payload.get("expires_in", 3600))
        _token_cache[cache_key] = (token, now + max(60, expires_in - 600))
        return token


def _resolve_creds(credentials: dict[str, Any] | None) -> tuple[str, str, str]:
    creds = credentials or {}
    tenant = (creds.get("tenant_id") or "").strip()
    client_id = (creds.get("client_id") or "").strip()
    client_secret = (creds.get("client_secret") or "").strip()
    if not (tenant and client_id and client_secret):
        raise ValueError(
            "msgraph: credentials must include tenant_id + client_id + client_secret"
        )
    return tenant, client_id, client_secret


def _mime_allowed(mime: str | None, whitelist: list[str]) -> bool:
    if not whitelist:
        return True
    return (mime or "") in whitelist


class MSGraphConnector(KBConnector):
    """SharePoint / OneDrive via Microsoft Graph delta API."""

    name = "msgraph"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        drive_id = (config.get("drive_id") or "").strip()
        if not drive_id:
            logger.warning("msgraph: missing config.drive_id")
            return

        try:
            tenant, client_id, client_secret = _resolve_creds(credentials)
        except ValueError as exc:
            logger.warning("msgraph: %s", exc)
            return

        whitelist = config.get("include_mime_types") or list(_DEFAULT_MIMES)

        token = await _get_access_token(tenant, client_id, client_secret)
        headers = {"Authorization": f"Bearer {token}"}

        # Use the saved deltaLink when present (incremental); else
        # call /delta with no token (initial full sync).
        next_link = cursor.get("delta_link") or f"{_GRAPH_BASE}/drives/{drive_id}/root/delta"

        seen = 0
        new_delta_link: str | None = None

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            while next_link:
                resp = await client.get(next_link, headers=headers)
                if resp.status_code == 401:
                    # Token expired between cache and call — refresh once.
                    _token_cache.pop(f"{tenant}|{client_id}", None)
                    token = await _get_access_token(tenant, client_id, client_secret)
                    headers["Authorization"] = f"Bearer {token}"
                    resp = await client.get(next_link, headers=headers)
                if resp.status_code != 200:
                    logger.warning(
                        "msgraph delta failed: %s %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return
                data = resp.json()

                for item in data.get("value", []) or []:
                    # Folders + deletions skipped — the connector
                    # framework doesn't model deletes yet.
                    if item.get("folder") or item.get("deleted"):
                        continue
                    file = item.get("file") or {}
                    mime = file.get("mimeType")
                    if not _mime_allowed(mime, whitelist):
                        continue

                    when_str = item.get("lastModifiedDateTime")
                    when = None
                    if isinstance(when_str, str):
                        try:
                            when = datetime.fromisoformat(
                                when_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            when = None

                    yield ConnectorResource(
                        resource_id=item["id"],
                        filename=item.get("name") or item["id"],
                        mime_type=mime,
                        size=item.get("size"),
                        # Graph exposes hashes for items > a few KB;
                        # prefer SHA-256 → quickXor → fall back to
                        # SHA-256 of fetched bytes.
                        content_hash=(
                            (file.get("hashes") or {}).get("sha256Hash")
                            or (file.get("hashes") or {}).get("quickXorHash")
                            or None
                        ),
                        modified_at=when,
                        metadata={
                            "drive_id": drive_id,
                            "etag": item.get("eTag"),
                            "web_url": item.get("webUrl"),
                        },
                    )
                    seen += 1
                    if seen >= _LIST_BUDGET:
                        # Save the current @odata.nextLink (NOT the
                        # deltaLink) so we resume mid-delta on the
                        # next tick.
                        cursor["delta_link"] = data.get("@odata.nextLink") or next_link
                        return

                # End-of-feed markers:
                #   @odata.nextLink → more changes in this delta call
                #   @odata.deltaLink → use this on the next sync
                next_link = data.get("@odata.nextLink")
                if not next_link:
                    new_delta_link = data.get("@odata.deltaLink")
                    break

        # Stash the deltaLink — finalize_cursor below will pick it up.
        cursor["_pending_delta_link"] = new_delta_link

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        drive_id = (config.get("drive_id") or "").strip()
        tenant, client_id, client_secret = _resolve_creds(credentials)
        token = await _get_access_token(tenant, client_id, client_secret)

        url = f"{_GRAPH_BASE}/drives/{drive_id}/items/{resource.resource_id}/content"
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True,
            )
            resp.raise_for_status()
            data = resp.content

        if not resource.content_hash:
            resource.content_hash = hashlib.sha256(data).hexdigest()
        resource.size = len(data)
        return data

    def advance_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        resource: ConnectorResource,
    ) -> dict[str, Any]:
        # Graph delta is opaque-token-based — we don't merge per
        # resource; finalize_cursor stamps the deltaLink saved
        # during list_resources.
        return current_cursor

    def finalize_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        last_run_at: datetime,
    ) -> dict[str, Any]:
        out = {**current_cursor, "last_run_at": last_run_at.isoformat()}
        pending = out.pop("_pending_delta_link", None)
        if pending:
            out["delta_link"] = pending
        return out
