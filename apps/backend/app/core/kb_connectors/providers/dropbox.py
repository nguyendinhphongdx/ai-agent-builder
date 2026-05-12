"""Dropbox KB connector.

Auth: long-lived access token (or refresh-token flow output)
pasted into the credential. Full OAuth callback flow lands when
the public marketplace UI ships.

Config:
  path                root to crawl, default "" (entire Dropbox).
                      Must start with "/" or be empty.
  recursive           default true.
  include_globs       default: ['*.pdf','*.docx','*.doc','*.md',
                                '*.txt','*.html','*.htm','*.pptx',
                                '*.xlsx']

Credentials (per-KB ai_credential row, Fernet-decrypted):
  access_token        ``sl.*`` or ``sk.*`` Dropbox token. Read
                      access scopes ``files.metadata.read`` +
                      ``files.content.read`` are enough.

Incremental sync: Dropbox's pagination cursor IS the incremental
sync mechanism. The cursor returned by ``/list_folder`` /
``/list_folder/continue`` survives until you next call with it;
between calls Dropbox accumulates change events and returns only
the diff. Same idea as MS Graph delta, different shape.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from fnmatch import fnmatch
from typing import Any, AsyncIterator

import httpx

from app.core.kb_connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_DROPBOX_API = "https://api.dropboxapi.com/2"
_DROPBOX_CONTENT = "https://content.dropboxapi.com/2"
_TIMEOUT = 15.0
_LIST_BUDGET = 500

_DEFAULT_GLOBS = (
    "*.pdf", "*.docx", "*.doc", "*.md", "*.txt", "*.html", "*.htm",
    "*.pptx", "*.xlsx",
)


def _matches_glob(name: str, globs: list[str]) -> bool:
    leaf = name.rsplit("/", 1)[-1].lower()
    return any(fnmatch(leaf, g) for g in globs)


def _normalise_path(path: str) -> str:
    """Dropbox wants ``""`` for root; ``"/folder"`` for everything
    else. Tolerate both leading-slash and bare strings from FE."""
    p = (path or "").strip()
    if not p or p == "/":
        return ""
    if not p.startswith("/"):
        return "/" + p
    return p.rstrip("/") or ""


class DropboxConnector(KBConnector):
    name = "dropbox"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        token = ((credentials or {}).get("access_token") or "").strip()
        if not token:
            logger.warning("dropbox: missing credentials.access_token")
            return

        path = _normalise_path(config.get("path", ""))
        recursive = bool(config.get("recursive", True))
        globs = config.get("include_globs") or list(_DEFAULT_GLOBS)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Cursor field ``dropbox_cursor`` — opaque token Dropbox
        # uses for delta-since-last-call. When absent, do a fresh
        # ``/list_folder`` (initial sync).
        dbx_cursor = cursor.get("dropbox_cursor")
        seen = 0

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            if dbx_cursor:
                resp = await client.post(
                    f"{_DROPBOX_API}/files/list_folder/continue",
                    headers=headers,
                    json={"cursor": dbx_cursor},
                )
            else:
                resp = await client.post(
                    f"{_DROPBOX_API}/files/list_folder",
                    headers=headers,
                    json={
                        "path": path,
                        "recursive": recursive,
                        "include_deleted": False,
                        "include_non_downloadable_files": False,
                    },
                )

            while True:
                if resp.status_code == 409:
                    # Stale cursor (e.g. workspace re-attached).
                    # Reset and full-sync next tick. We still need
                    # to yield nothing now so the orchestrator doesn't
                    # treat this as a hard error.
                    cursor.pop("dropbox_cursor", None)
                    logger.info("dropbox: cursor reset (409)")
                    return
                if resp.status_code != 200:
                    logger.warning(
                        "dropbox list failed: %s %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    return
                data = resp.json()

                for entry in data.get("entries", []) or []:
                    if entry.get(".tag") != "file":
                        continue
                    name = entry.get("name") or ""
                    if not _matches_glob(name, globs):
                        continue
                    when_str = entry.get("server_modified")
                    when = None
                    if isinstance(when_str, str):
                        try:
                            when = datetime.fromisoformat(
                                when_str.replace("Z", "+00:00")
                            )
                        except ValueError:
                            when = None
                    yield ConnectorResource(
                        resource_id=entry.get("path_lower")
                        or entry.get("id")
                        or "",
                        filename=name,
                        mime_type=None,
                        size=entry.get("size"),
                        # Dropbox content_hash is a SHA-256 over
                        # 4MB-block hashes (their own algorithm) —
                        # still stable across runs so we use it
                        # for dedup.
                        content_hash=entry.get("content_hash"),
                        modified_at=when,
                        metadata={
                            "rev": entry.get("rev"),
                            "path_display": entry.get("path_display"),
                        },
                    )
                    seen += 1
                    if seen >= _LIST_BUDGET:
                        # Save the latest cursor + bail — next
                        # tick will resume here.
                        cursor["_pending_dropbox_cursor"] = data.get("cursor")
                        return

                if not data.get("has_more"):
                    cursor["_pending_dropbox_cursor"] = data.get("cursor")
                    return

                resp = await client.post(
                    f"{_DROPBOX_API}/files/list_folder/continue",
                    headers=headers,
                    json={"cursor": data["cursor"]},
                )

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        token = ((credentials or {}).get("access_token") or "").strip()
        if not token:
            raise PermissionError("dropbox: access_token missing")

        # Dropbox download uses a special API style: the file path
        # goes in a JSON-encoded header, not the request body.
        import json as _json

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{_DROPBOX_CONTENT}/files/download",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Dropbox-API-Arg": _json.dumps(
                        {"path": resource.resource_id}
                    ),
                },
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
        # Per-resource cursor doesn't apply — Dropbox cursors are
        # opaque tokens stamped in ``finalize_cursor``.
        return current_cursor

    def finalize_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        last_run_at: datetime,
    ) -> dict[str, Any]:
        out = {**current_cursor, "last_run_at": last_run_at.isoformat()}
        pending = out.pop("_pending_dropbox_cursor", None)
        if pending:
            out["dropbox_cursor"] = pending
        return out
