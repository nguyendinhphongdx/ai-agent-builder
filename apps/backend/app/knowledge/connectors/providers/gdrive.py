"""Google Drive KB connector — service-account variant.

Auth: a GCP service account with the ``drive.readonly`` scope.
Admin shares the target folder (or whole shared-drive) with the
SA's email; we use the SA JSON to authenticate. This bypasses the
3-legged OAuth dance — full OAuth-with-callback lands in a later
block when the public marketplace ships.

Config:
  folder_id          optional — restrict the crawl to one folder
                     (and all descendants). Omit to scan everything
                     the SA can see.
  shared_drive_id    optional — when set, queries go against this
                     shared drive (supportsAllDrives=True).
  include_mime_types default: docs, sheets, slides, PDFs, plain
                     text, markdown.

Credentials (per-KB ai_credential row, Fernet-decrypted):
  service_account_json   inline JSON content of the SA key.

Incremental sync: Drive's ``modifiedTime`` field with the API's
``orderBy=modifiedTime desc`` driver — once we hit a file older
than the cursor, every remaining one is older too.

Native Google Doc / Sheet / Slides files get exported to PDF
during fetch — that's the most reliable cross-format extractor
target. Plain files (PDF / DOCX / TXT / etc.) come down as bytes
verbatim.
"""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from app.knowledge.connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_LIST_BUDGET = 500
_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Native Google formats → export MIME they should download as.
_EXPORT_MIME = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/pdf",
    "application/vnd.google-apps.presentation": "application/pdf",
}

_DEFAULT_MIME_FILTER = (
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
)


def _build_service(credentials: dict[str, Any] | None):
    """Lazy SDK import — google-api-python-client + google-auth.

    Both already in the dep tree (langchain-google-genai pulls
    google-auth; google-api-python-client is the standard SDK we
    rely on for Drive). Declaring explicitly in pyproject for
    discoverability.
    """
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = credentials or {}
    sa_json = (creds.get("service_account_json") or "").strip()
    if not sa_json:
        raise ValueError(
            "gdrive: credentials.service_account_json is required"
        )
    info = json.loads(sa_json)
    sa_creds = service_account.Credentials.from_service_account_info(
        info, scopes=_DRIVE_SCOPES
    )
    return build("drive", "v3", credentials=sa_creds, cache_discovery=False)


def _build_query(
    *, folder_id: str | None, mime_types: list[str]
) -> str:
    """Compose a Drive search query.

    Use ``trashed = false`` always so deleted files don't recur.
    MIME filter combined with ``or`` so a doc OR a pdf OR ... all
    match; folder restriction with ``and`` if set.
    """
    parts: list[str] = ["trashed = false"]
    if mime_types:
        mime_clause = " or ".join(f"mimeType = '{m}'" for m in mime_types)
        parts.append(f"({mime_clause})")
    if folder_id:
        parts.append(f"'{folder_id}' in parents")
    return " and ".join(parts)


class GoogleDriveConnector(KBConnector):
    name = "gdrive"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        try:
            service = await asyncio.to_thread(_build_service, credentials)
        except ValueError as exc:
            logger.warning("gdrive connector: %s", exc)
            return

        last_iso = cursor.get("last_modified_iso")
        last_mod = datetime.fromisoformat(last_iso) if last_iso else None

        folder_id = (config.get("folder_id") or "").strip() or None
        shared_drive_id = (config.get("shared_drive_id") or "").strip() or None
        mime_types = config.get("include_mime_types") or list(_DEFAULT_MIME_FILTER)

        query = _build_query(folder_id=folder_id, mime_types=mime_types)

        common_kwargs: dict[str, Any] = {
            "q": query,
            "orderBy": "modifiedTime desc",
            "fields": (
                "nextPageToken,"
                "files(id,name,mimeType,size,modifiedTime,md5Checksum)"
            ),
            "pageSize": 100,
        }
        if shared_drive_id:
            common_kwargs.update(
                corpora="drive",
                driveId=shared_drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )

        seen = 0
        page_token: str | None = None
        while True:
            kwargs = {**common_kwargs}
            if page_token:
                kwargs["pageToken"] = page_token

            def _list_call(kw=kwargs):
                return service.files().list(**kw).execute()

            data = await asyncio.to_thread(_list_call)
            files = data.get("files", []) or []

            for f in files:
                modified_str = f.get("modifiedTime")
                mtime = None
                if modified_str:
                    try:
                        mtime = datetime.fromisoformat(
                            modified_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        mtime = None
                # Drive returns desc — once we hit older, the rest
                # is older too.
                if (
                    last_mod is not None
                    and mtime is not None
                    and mtime <= last_mod
                ):
                    return

                yield ConnectorResource(
                    resource_id=f["id"],
                    filename=f.get("name") or f["id"],
                    mime_type=f.get("mimeType"),
                    size=(int(f["size"]) if f.get("size") else None),
                    # md5Checksum present for binary uploads;
                    # native Google formats don't expose it.
                    content_hash=f.get("md5Checksum") or None,
                    modified_at=mtime,
                    metadata={
                        "drive_id": shared_drive_id,
                        "folder_id": folder_id,
                    },
                )
                seen += 1
                if seen >= _LIST_BUDGET:
                    return

            page_token = data.get("nextPageToken")
            if not page_token:
                return

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        service = await asyncio.to_thread(_build_service, credentials)

        def _download() -> bytes:
            from googleapiclient.http import MediaIoBaseDownload

            mime = resource.mime_type or ""
            export_as = _EXPORT_MIME.get(mime)
            if export_as:
                # Native Google file → export route.
                request = service.files().export_media(
                    fileId=resource.resource_id, mimeType=export_as
                )
            else:
                request = service.files().get_media(
                    fileId=resource.resource_id, supportsAllDrives=True
                )
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()
            return buf.getvalue()

        data = await asyncio.to_thread(_download)
        if not resource.content_hash:
            resource.content_hash = hashlib.sha256(data).hexdigest()
        # Stamp the post-export mime hint so the parser picks the
        # right backend (PDF for exported docs / sheets / slides).
        if resource.mime_type in _EXPORT_MIME:
            resource.metadata["exported_as"] = _EXPORT_MIME[resource.mime_type]
        return data

    def advance_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        resource: ConnectorResource,
    ) -> dict[str, Any]:
        mtime = resource.modified_at
        if mtime is None:
            return current_cursor
        prev_iso = current_cursor.get("last_modified_iso")
        if prev_iso is None or datetime.fromisoformat(prev_iso) < mtime:
            return {**current_cursor, "last_modified_iso": mtime.isoformat()}
        return current_cursor

    def finalize_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        last_run_at: datetime,
    ) -> dict[str, Any]:
        out = {**current_cursor, "last_run_at": last_run_at.isoformat()}
        # When no file in this run had a modifiedTime (unlikely —
        # Drive always returns it) we still want some watermark.
        if "last_modified_iso" not in out:
            out["last_modified_iso"] = last_run_at.astimezone(
                timezone.utc
            ).isoformat()
        return out
