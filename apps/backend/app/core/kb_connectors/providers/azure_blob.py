"""Azure Blob Storage KB connector.

Third cloud-storage provider; same shape as S3 + GCS but the
Azure SDK has its own auth pattern (connection string OR account
key OR SAS token). We support all three.

Config:
  account_name      required when not using a connection string
  container         required — blob container name
  prefix            optional — blob name prefix
  include_globs     default: ['*.pdf','*.docx','*.doc','*.md',
                              '*.txt','*.html','*.htm']

Credentials (per-KB ai_credential row, Fernet-decrypted):
  connection_string   complete Azure Storage connection string;
                      preferred — wraps the account name + key
                      + endpoint suffix into one secret.
  account_key         shared-key auth when only the key is known
                      (account_name must be in config).
  sas_token           SAS token alternative — read-only, time-
                      limited credentials.
  endpoint_suffix     default ``core.windows.net``; override for
                      sovereign clouds (e.g. Azure Government).

Incremental sync: blob ``last_modified`` (datetime, UTC) drives
the watermark. Same per-tick budget pattern as S3 / GCS.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any, AsyncIterator

from app.core.kb_connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_LIST_BUDGET = 1000
_DEFAULT_GLOBS = ("*.pdf", "*.docx", "*.doc", "*.md", "*.txt", "*.html", "*.htm")


def _build_service_client(
    credentials: dict[str, Any] | None, config: dict[str, Any]
):
    """Lazy SDK import — azure-storage-blob is heavy."""
    from azure.storage.blob import BlobServiceClient

    creds = credentials or {}
    conn_str = (creds.get("connection_string") or "").strip()
    if conn_str:
        return BlobServiceClient.from_connection_string(conn_str)

    account_name = (config.get("account_name") or "").strip()
    if not account_name:
        raise ValueError(
            "azure_blob: account_name required when connection_string is not set"
        )
    suffix = (config.get("endpoint_suffix") or "core.windows.net").strip()
    account_url = f"https://{account_name}.blob.{suffix}"

    account_key = (creds.get("account_key") or "").strip()
    sas_token = (creds.get("sas_token") or "").strip()
    if account_key:
        return BlobServiceClient(account_url=account_url, credential=account_key)
    if sas_token:
        return BlobServiceClient(account_url=account_url, credential=sas_token)
    # Last resort — DefaultAzureCredential (managed identity etc.).
    # The auth chain is heavy; users typically pick one of the
    # above. Import locally so the SDK doesn't probe identity at
    # import time.
    from azure.identity import DefaultAzureCredential

    return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())


def _matches_glob(name: str, globs: list[str]) -> bool:
    leaf = name.rsplit("/", 1)[-1].lower()
    return any(fnmatch(leaf, g) for g in globs)


class AzureBlobConnector(KBConnector):
    name = "azure_blob"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        container = (config.get("container") or "").strip()
        if not container:
            logger.warning("azure_blob connector: missing config.container")
            return

        prefix = (config.get("prefix") or "").lstrip("/")
        globs = config.get("include_globs") or list(_DEFAULT_GLOBS)
        last_iso = cursor.get("last_modified_iso")
        last_mod = datetime.fromisoformat(last_iso) if last_iso else None

        service = await asyncio.to_thread(_build_service_client, credentials, config)

        def _list_blobs() -> list[dict[str, Any]]:
            cc = service.get_container_client(container)
            # list_blobs returns a paginated iterable; materialise
            # into plain dicts so the connector contract doesn't
            # leak the BlobProperties object.
            out: list[dict[str, Any]] = []
            for b in cc.list_blobs(name_starts_with=prefix or None):
                out.append(
                    {
                        "name": b.name,
                        "size": b.size,
                        "last_modified": b.last_modified,
                        "etag": b.etag,
                        "content_type": (b.content_settings or None)
                        and b.content_settings.content_type,
                        "content_md5": (b.content_settings or None)
                        and b.content_settings.content_md5,
                    }
                )
            return out

        blobs = await asyncio.to_thread(_list_blobs)

        seen = 0
        for blob in blobs:
            name = blob["name"]
            if name.endswith("/"):
                continue
            if not _matches_glob(name, globs):
                continue
            mtime = blob.get("last_modified")
            if isinstance(mtime, datetime) and mtime.tzinfo is None:
                mtime = mtime.replace(tzinfo=timezone.utc)
            if last_mod is not None and mtime is not None and mtime <= last_mod:
                continue

            md5 = blob.get("content_md5")
            # content_md5 comes back as bytes; hex for consistency
            # with our other hash storage.
            hash_str = md5.hex() if isinstance(md5, (bytes, bytearray)) else None
            if not hash_str and blob.get("etag"):
                hash_str = str(blob["etag"]).strip('"')

            yield ConnectorResource(
                resource_id=name,
                filename=name.rsplit("/", 1)[-1],
                mime_type=blob.get("content_type"),
                size=blob.get("size"),
                content_hash=hash_str,
                modified_at=mtime,
                metadata={"container": container},
            )
            seen += 1
            if seen >= _LIST_BUDGET:
                return

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        container = (config.get("container") or "").strip()
        service = await asyncio.to_thread(_build_service_client, credentials, config)

        def _download() -> bytes:
            blob_client = service.get_blob_client(
                container=container, blob=resource.resource_id
            )
            return blob_client.download_blob().readall()

        data = await asyncio.to_thread(_download)
        if not resource.content_hash:
            resource.content_hash = hashlib.sha256(data).hexdigest()
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
