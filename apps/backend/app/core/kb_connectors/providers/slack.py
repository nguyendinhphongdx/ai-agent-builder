"""Slack files KB connector.

Auth: OAuth bot token from the ``oauth_connections`` table —
resolved by ``sync.py`` and injected as
``credentials["access_token"]`` before this connector runs. The
admin connects Slack from the Connections page, then references
the connection id when creating the KB connector.

Discovery shape:
  config.oauth_connection_id  required — points at the Slack OAuth
                              connection that owns the bot token
  config.channel              optional — restrict to one channel id
                              (bot must be in it). Empty = every
                              channel the bot can see files in.
  config.types                optional — comma-separated Slack
                              filetypes to keep (e.g. ``pdf,docx``).
                              Empty = every downloadable type.
  config.budget               optional — max files per tick. Default
                              ``_LIST_BUDGET``.

Incremental sync: keyed on Slack's ``files.list`` ``ts_from`` (file
``created`` timestamp, unix-epoch seconds). On each tick we walk
files created after ``cursor.last_ts`` until the budget is hit or
the listing ends; finalize stamps ``last_ts`` to the run timestamp
so the next tick picks up only newer files.

Content: downloaded via ``url_private_download`` with the same
bearer token. Slack-native "posts" / "snippets" / "canvases"
expose no download URL — those are skipped in v1.

Rate limits: Slack publishes per-method tiers; ``files.list`` is
Tier 3 (~50 req/min) and downloads are Tier 4 (~100 req/min). The
connector serialises requests so even big workspaces tick through
politely. Hard 429s pause for the ``Retry-After`` window.

Required scopes (configured on the OAuth provider): ``files:read``
(list + download), ``channels:read`` / ``channels:history`` (for
channel-restricted listing). The bot must be /invited to a channel
to see its files.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx

from app.core.kb_connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_SLACK_API = "https://slack.com/api"
_TIMEOUT = 30.0
# Per-tick budget so a never-synced workspace with 50k files doesn't
# tie up the runner for an hour.
_LIST_BUDGET = 200
# Slack supports up to 200 per page on files.list.
_PAGE_SIZE = 100


def _client(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_SLACK_API,
        headers={"Authorization": f"Bearer {token}"},
        timeout=_TIMEOUT,
    )


async def _slack_call(
    client: httpx.AsyncClient, path: str, params: dict[str, Any]
) -> dict[str, Any]:
    """Slack returns 200 with ``ok=false`` on logical errors. Wrap so
    callers get a single failure shape."""
    resp = await client.get(path, params=params)
    if resp.status_code == 429:
        retry_after = float(resp.headers.get("Retry-After", "1") or 1)
        logger.info("slack: 429 — backing off %.1fs", retry_after)
        await asyncio.sleep(min(retry_after, 30.0))
        resp = await client.get(path, params=params)
    if resp.status_code >= 400:
        raise RuntimeError(
            f"slack {path} http {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(
            f"slack {path} api error: {data.get('error') or 'unknown'}"
        )
    return data


def _file_filename(file: dict[str, Any]) -> str:
    # Slack's ``name`` is the user-visible filename; ``title`` falls
    # back to it. Some uploads have empty name (drag-drop screenshots
    # named "image.png" by Slack itself) — synthesise from id.
    name = (file.get("name") or "").strip()
    if name:
        return name
    title = (file.get("title") or "").strip()
    if title:
        return title
    return f"slack-file-{file.get('id', 'unknown')}"


def _file_modified_at(file: dict[str, Any]) -> datetime | None:
    ts = file.get("created")
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (ValueError, OSError):
        return None


def _is_downloadable(file: dict[str, Any]) -> bool:
    """Skip Slack-native virtual files (posts, snippets, canvases).

    These have no ``url_private_download`` and their content is in
    a JSON ``content`` field that needs separate rendering. Out of
    scope for v1.
    """
    if not file.get("url_private_download"):
        return False
    # External-source files (Google Drive shares, Dropbox links)
    # are visible to the Slack API but the download URL redirects
    # to the source — we'd need that source's auth to fetch. Skip.
    if file.get("is_external"):
        return False
    return True


class SlackFilesConnector(KBConnector):
    name = "slack"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        token = (credentials or {}).get("access_token", "").strip()
        if not token:
            logger.warning(
                "slack connector: missing access_token (oauth_connection_id wired?)"
            )
            return

        channel = (config.get("channel") or "").strip() or None
        types_filter = (config.get("types") or "").strip() or None
        budget = int(config.get("budget") or _LIST_BUDGET)

        last_ts = cursor.get("last_ts")
        params: dict[str, Any] = {"count": _PAGE_SIZE, "page": 1}
        if channel:
            params["channel"] = channel
        if types_filter:
            params["types"] = types_filter
        if last_ts:
            # Slack's ts_from is exclusive of the boundary, so we
            # don't re-emit the watermark file.
            params["ts_from"] = float(last_ts)

        seen = 0
        async with _client(token) as client:
            while True:
                data = await _slack_call(client, "/files.list", params)
                files = data.get("files") or []
                if not files:
                    return
                for file in files:
                    if not _is_downloadable(file):
                        continue
                    resource_id = file.get("id")
                    if not resource_id:
                        continue
                    yield ConnectorResource(
                        resource_id=resource_id,
                        filename=_file_filename(file),
                        mime_type=file.get("mimetype"),
                        size=file.get("size"),
                        # Slack doesn't surface an etag; rely on
                        # SHA-256 of bytes downstream (content_hash
                        # left None here triggers that path).
                        content_hash=None,
                        modified_at=_file_modified_at(file),
                        metadata={
                            "slack_file_id": resource_id,
                            "slack_user": file.get("user"),
                            "slack_channels": file.get("channels") or [],
                            "permalink": file.get("permalink"),
                            "url_private_download": file.get(
                                "url_private_download"
                            ),
                            "filetype": file.get("filetype"),
                        },
                    )
                    seen += 1
                    if seen >= budget:
                        return

                paging = data.get("paging") or {}
                current = paging.get("page") or params["page"]
                total_pages = paging.get("pages") or current
                if current >= total_pages:
                    return
                params["page"] = current + 1

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        token = (credentials or {}).get("access_token", "").strip()
        url = (resource.metadata or {}).get("url_private_download")
        if not token or not url:
            raise RuntimeError(
                "slack connector: missing token or url_private_download"
            )
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"slack download {resource.resource_id} failed: "
                    f"{resp.status_code} {resp.text[:200]}"
                )
            # Sanity check — Slack sometimes returns the login page
            # (HTML) when the token can't see the file. The HTML
            # shape is detectable by Content-Type.
            ctype = resp.headers.get("content-type", "")
            if "text/html" in ctype and not (
                resource.mime_type and "html" in resource.mime_type
            ):
                snippet = hashlib.sha256(resp.content).hexdigest()[:8]
                raise RuntimeError(
                    f"slack download returned HTML — token likely lacks "
                    f"access to file (content sha8={snippet})"
                )
            return resp.content

    def advance_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        resource: ConnectorResource,
    ) -> dict[str, Any]:
        # Slack files.list returns newest-first descending; we track
        # the *latest* timestamp seen so the next run continues from
        # there. ``modified_at`` is None only for malformed files.
        if resource.modified_at is None:
            return current_cursor
        ts = resource.modified_at.timestamp()
        last_ts = float(current_cursor.get("last_ts") or 0.0)
        if ts > last_ts:
            return {**current_cursor, "last_ts": ts}
        return current_cursor

    def finalize_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        last_run_at: datetime,
    ) -> dict[str, Any]:
        # If we saw at least one file, ``advance_cursor`` already set
        # ``last_ts`` to that file's timestamp. If we saw zero, stamp
        # the run timestamp so empty ticks still advance the cursor —
        # otherwise a quiet workspace would re-scan from the same
        # point forever.
        out = {**current_cursor, "last_run_at": last_run_at.isoformat()}
        if "last_ts" not in out:
            out["last_ts"] = last_run_at.timestamp()
        return out
