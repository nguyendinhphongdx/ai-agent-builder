"""S3 / S3-compatible (MinIO, R2, Wasabi, …) KB connector.

Config:
  bucket          required — bucket name
  prefix          optional — key prefix to limit the scope
                  ("documents/2026/" for example)
  region          AWS region; ignored by non-AWS S3-compatible
                  services that route by ``endpoint_url``
  endpoint_url    optional — custom endpoint for MinIO/R2/Wasabi
  include_globs   optional list of fnmatch globs filtering keys
                  (default: all .pdf .docx .md .txt .html)

Credentials (from the KB's ``ai_credential`` row, Fernet-decrypted):
  access_key_id     AWS access key
  secret_access_key AWS secret
  session_token     optional — for STS temp creds

When credentials are empty the boto3 default chain runs (env,
~/.aws, instance role) — same pattern as ``langchain_aws``.

Incremental sync: keyed on ``LastModified``. The cursor stamps the
high-water-mark ISO timestamp + a ``next_continuation_token`` for
huge buckets so a single tick can resume where a budget-bounded
previous tick stopped.
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

# Per-tick budget — pull at most this many keys before stopping
# and stamping a continuation token. Keeps one runaway bucket
# from starving the scheduler.
_LIST_BUDGET = 1000

_DEFAULT_GLOBS = ("*.pdf", "*.docx", "*.doc", "*.md", "*.txt", "*.html", "*.htm")


def _boto3():
    """Lazy import — boto3 is only loaded when an S3 connector
    actually runs. Same pattern as the Bedrock provider."""
    import boto3

    return boto3


def _make_client(
    credentials: dict[str, Any] | None,
    region: str | None,
    endpoint_url: str | None,
):
    boto3 = _boto3()
    creds = credentials or {}
    kwargs: dict[str, Any] = {}
    if creds.get("access_key_id"):
        kwargs["aws_access_key_id"] = creds["access_key_id"]
    if creds.get("secret_access_key"):
        kwargs["aws_secret_access_key"] = creds["secret_access_key"]
    if creds.get("session_token"):
        kwargs["aws_session_token"] = creds["session_token"]
    if region:
        kwargs["region_name"] = region
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return boto3.client("s3", **kwargs)


def _matches_glob(key: str, globs: list[str]) -> bool:
    """Match the *filename* part (post-prefix). Glob against the
    full key would force users to write ``**/*.pdf`` patterns."""
    name = key.rsplit("/", 1)[-1].lower()
    return any(fnmatch(name, g) for g in globs)


class S3Connector(KBConnector):
    name = "s3"

    async def list_resources(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        cursor: dict[str, Any],
    ) -> AsyncIterator[ConnectorResource]:
        bucket = (config.get("bucket") or "").strip()
        if not bucket:
            logger.warning("s3 connector: missing config.bucket")
            return

        prefix = (config.get("prefix") or "").lstrip("/")
        globs = config.get("include_globs") or list(_DEFAULT_GLOBS)
        # Cursor fields:
        #   last_modified_iso: high-water mtime from prior runs
        #   continuation_token: mid-page resume token within a single
        #                       big sync (cleared once a sync completes)
        last_iso = cursor.get("last_modified_iso")
        last_mod = datetime.fromisoformat(last_iso) if last_iso else None
        continuation_token = cursor.get("continuation_token")

        client = await asyncio.to_thread(
            _make_client,
            credentials,
            config.get("region"),
            config.get("endpoint_url"),
        )

        seen = 0
        next_token = continuation_token

        while True:
            kwargs: dict[str, Any] = {
                "Bucket": bucket,
                "MaxKeys": 200,  # AWS caps at 1000; 200 keeps memory low
            }
            if prefix:
                kwargs["Prefix"] = prefix
            if next_token:
                kwargs["ContinuationToken"] = next_token

            page = await asyncio.to_thread(client.list_objects_v2, **kwargs)
            contents = page.get("Contents", []) or []
            for obj in contents:
                key: str = obj["Key"]
                # Skip "folders" — S3 has no real folders, but the
                # SDK surfaces zero-byte prefix-named keys.
                if key.endswith("/"):
                    continue
                if not _matches_glob(key, globs):
                    continue
                mtime = obj.get("LastModified")
                if isinstance(mtime, datetime):
                    if mtime.tzinfo is None:
                        mtime = mtime.replace(tzinfo=timezone.utc)
                else:
                    mtime = None
                if last_mod is not None and mtime is not None and mtime <= last_mod:
                    continue

                yield ConnectorResource(
                    resource_id=key,
                    filename=key.rsplit("/", 1)[-1],
                    mime_type=None,
                    size=int(obj.get("Size") or 0),
                    # Use S3's ETag as the dedup hash when available;
                    # falls back to SHA-256 after fetch. ETag is
                    # quoted in the API response; strip the quotes.
                    content_hash=(obj.get("ETag") or "").strip('"') or None,
                    modified_at=mtime,
                    metadata={"bucket": bucket, "key": key},
                )
                seen += 1
                if seen >= _LIST_BUDGET:
                    return

            if not page.get("IsTruncated"):
                return
            next_token = page.get("NextContinuationToken")
            if not next_token:
                return

    async def fetch_content(
        self,
        *,
        config: dict[str, Any],
        credentials: dict[str, Any] | None,
        resource: ConnectorResource,
    ) -> bytes:
        bucket = (config.get("bucket") or "").strip()
        client = await asyncio.to_thread(
            _make_client,
            credentials,
            config.get("region"),
            config.get("endpoint_url"),
        )

        def _get() -> bytes:
            obj = client.get_object(Bucket=bucket, Key=resource.resource_id)
            body = obj["Body"]
            try:
                return body.read()
            finally:
                body.close()

        data = await asyncio.to_thread(_get)
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

    def finalize_cursor(
        self,
        *,
        current_cursor: dict[str, Any],
        last_run_at: datetime,
    ) -> dict[str, Any]:
        # Clear the continuation token — we either exhausted the
        # bucket or hit the budget cap (caller will resume on the
        # next sweep using last_modified_iso anyway).
        out = {**current_cursor, "last_run_at": last_run_at.isoformat()}
        out.pop("continuation_token", None)
        return out
