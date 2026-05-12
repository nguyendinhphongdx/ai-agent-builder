"""Google Cloud Storage KB connector.

Mirrors the S3 provider's shape — bucket + prefix + glob filter +
LastModified incremental sync — but uses ``google-cloud-storage``
instead of boto3 because the auth + API surface differ enough to
warrant a separate module.

Config:
  bucket           required — GCS bucket name
  prefix           optional — object name prefix
  include_globs    default: ['*.pdf','*.docx','*.doc','*.md',
                             '*.txt','*.html','*.htm']

Credentials (per-KB ai_credential row, Fernet-decrypted):
  service_account_json   inline JSON content of a GCP SA key. When
                         empty, the ``google.cloud.storage.Client``
                         default chain runs: GOOGLE_APPLICATION_
                         CREDENTIALS env, gcloud user creds,
                         metadata server (GKE / Cloud Run).

Incremental sync: GCS ``Blob.updated`` (datetime, UTC) is the
high-water mark. The list_blobs iterator is paginated by the SDK
already; we cap at _LIST_BUDGET per tick to avoid one big bucket
starving the scheduler.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone
from fnmatch import fnmatch
from typing import Any, AsyncIterator

from app.core.kb_connectors.base import ConnectorResource, KBConnector

logger = logging.getLogger("agentforge")

_LIST_BUDGET = 1000
_DEFAULT_GLOBS = ("*.pdf", "*.docx", "*.doc", "*.md", "*.txt", "*.html", "*.htm")


def _build_client(credentials: dict[str, Any] | None):
    """Lazy SDK import — keeps google-cloud-storage out of the
    cold-start path for tenants who never use GCS."""
    from google.cloud import storage as gcs

    creds = credentials or {}
    sa_json = (creds.get("service_account_json") or "").strip()
    if sa_json:
        from google.oauth2 import service_account

        info = json.loads(sa_json)
        gcp_creds = service_account.Credentials.from_service_account_info(info)
        return gcs.Client(credentials=gcp_creds, project=info.get("project_id"))

    # Default credential chain — useful when the backend itself
    # runs on a GCP-managed VM with a service account attached.
    return gcs.Client()


def _matches_glob(name: str, globs: list[str]) -> bool:
    leaf = name.rsplit("/", 1)[-1].lower()
    return any(fnmatch(leaf, g) for g in globs)


class GCSConnector(KBConnector):
    name = "gcs"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        bucket = (config.get("bucket") or "").strip()
        if not bucket:
            logger.warning("gcs connector: missing config.bucket")
            return

        prefix = (config.get("prefix") or "").lstrip("/")
        globs = config.get("include_globs") or list(_DEFAULT_GLOBS)
        last_iso = cursor.get("last_modified_iso")
        last_mod = datetime.fromisoformat(last_iso) if last_iso else None

        client = await asyncio.to_thread(_build_client, credentials)

        def _list_blobs():
            bkt = client.bucket(bucket)
            # ``list_blobs`` returns an iterator that pages under
            # the hood; materialise lazily by yielding from it.
            return list(bkt.list_blobs(prefix=prefix or None, max_results=None))

        # GCS SDK is sync — chunk the listing to to_thread so we
        # don't park the event loop on a slow bucket.
        blobs = await asyncio.to_thread(_list_blobs)

        seen = 0
        for blob in blobs:
            name = blob.name
            if name.endswith("/"):
                continue
            if not _matches_glob(name, globs):
                continue
            updated = blob.updated  # tz-aware datetime
            if isinstance(updated, datetime) and updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if last_mod is not None and updated is not None and updated <= last_mod:
                continue

            yield ConnectorResource(
                resource_id=name,
                filename=name.rsplit("/", 1)[-1],
                mime_type=blob.content_type,
                size=blob.size,
                # GCS ``etag`` is a generation-aware identifier;
                # GCS ``md5_hash`` is the real content hash for
                # single-component uploads. Prefer md5 when present.
                content_hash=blob.md5_hash or blob.etag or None,
                modified_at=updated,
                metadata={"bucket": bucket, "generation": blob.generation},
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
        bucket = (config.get("bucket") or "").strip()
        client = await asyncio.to_thread(_build_client, credentials)

        def _download() -> bytes:
            blob = client.bucket(bucket).blob(resource.resource_id)
            return blob.download_as_bytes()

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
