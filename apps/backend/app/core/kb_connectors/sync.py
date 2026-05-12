"""Connector sync orchestration.

One entry point — :func:`run_connector(db, connector)` — that:
  1. Resolves the provider via the registry.
  2. Decrypts credentials.
  3. If config carries ``oauth_connection_id``, resolves a fresh
     bearer token via the OAuth connections service and injects it
     into the credentials dict — providers stay DB-free.
  4. Iterates the provider's resources.
  5. Per-resource: dedupes against existing Documents by
     content_hash, persists a new Document row, hands it off to
     the existing KB ingestion pipeline via the jobs queue.
  6. Advances + persists the cursor.

The orchestrator is provider-agnostic — adding a new connector
needs zero changes here.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.kb_connectors import (
    KBConnectorRunResult,
    build_connector,
)
from app.models.document import Document
from app.models.kb_connector import KBConnector as KBConnectorRow
from app.modules.jobs import types as job_types
from app.modules.jobs.producer import enqueue as enqueue_job
from app.modules.knowledge.service import get_knowledge_base_unscoped
from app.modules.oauth_connectors.service import get_access_token
from app.platform.config import settings
from app.platform.security.crypto import decrypt_secret
from app.platform.storage import generate_storage_key, get_storage

logger = logging.getLogger("agentforge")


def _decrypt_credentials(encrypted: str | None) -> dict | None:
    if not encrypted:
        return None
    try:
        return json.loads(decrypt_secret(encrypted))
    except (ValueError, json.JSONDecodeError):
        logger.exception("connector: failed to decrypt credentials blob")
        return None


async def _maybe_inject_oauth_token(
    db: AsyncSession,
    *,
    config: dict,
    credentials: dict | None,
) -> dict | None:
    """OAuth-backed connectors store the connection id in ``config``
    rather than a long-lived secret in ``credentials_encrypted``.

    Resolve the connection id to a fresh access token (refreshing if
    needed) and inject it as ``credentials.access_token`` so the
    provider implementation can stay stateless.

    Returns the (possibly enriched) credentials dict, or the original
    if no OAuth binding is configured.
    """
    raw_id = (config or {}).get("oauth_connection_id")
    if not raw_id:
        return credentials
    try:
        conn_id = uuid.UUID(str(raw_id))
    except (ValueError, TypeError):
        raise ValueError(
            f"invalid oauth_connection_id in connector config: {raw_id!r}"
        )
    token = await get_access_token(db, conn_id)
    merged = dict(credentials or {})
    merged["access_token"] = token
    merged["oauth_connection_id"] = str(conn_id)
    return merged


async def run_connector(
    db: AsyncSession, connector: KBConnectorRow
) -> KBConnectorRunResult:
    """Execute one sync pass for ``connector``. Returns a result with
    counts + new cursor; the caller commits.

    Errors are caught per-resource so a partial outage doesn't kill
    the whole run. Hard failures (unknown provider, invalid root,
    auth) abort early and stamp ``connector.last_error``.
    """
    provider = build_connector(connector.connector_type)
    if provider is None:
        connector.last_error = f"Unknown connector type: {connector.connector_type!r}"
        return KBConnectorRunResult(errors=[connector.last_error])

    kb = await get_knowledge_base_unscoped(db, connector.knowledge_base_id)
    if kb is None:
        connector.last_error = "Knowledge base missing"
        return KBConnectorRunResult(errors=[connector.last_error])

    credentials = _decrypt_credentials(connector.credentials_encrypted)
    try:
        credentials = await _maybe_inject_oauth_token(
            db, config=connector.config or {}, credentials=credentials
        )
    except ValueError as exc:
        # OAuth resolution failed (missing connection, expired refresh,
        # bad provider). Surface so the UI can prompt re-connect.
        connector.last_error = f"OAuth: {exc}"
        return KBConnectorRunResult(errors=[connector.last_error])
    cursor = dict(connector.sync_cursor or {})
    run_started = datetime.now(timezone.utc)
    result = KBConnectorRunResult(new_cursor=cursor)
    storage = get_storage()

    # Pull existing content hashes so we can dedupe without N round-trips.
    existing_hashes: set[str] = set(
        (
            await db.scalars(
                select(Document.content_hash).where(
                    Document.knowledge_base_id == kb.id,
                    Document.content_hash.is_not(None),
                )
            )
        ).all()
    )

    try:
        async for resource in provider.list_resources(
            config=connector.config or {},
            credentials=credentials,
            cursor=cursor,
        ):
            result.discovered += 1
            try:
                content_bytes = await provider.fetch_content(
                    config=connector.config or {},
                    credentials=credentials,
                    resource=resource,
                )
            except Exception as exc:  # noqa: BLE001 — per-resource isolation
                msg = f"fetch failed for {resource.resource_id}: {exc}"
                logger.warning("connector: %s", msg)
                result.failed += 1
                result.errors.append(msg[:500])
                continue

            content_hash = resource.content_hash or hashlib.sha256(
                content_bytes
            ).hexdigest()
            if content_hash in existing_hashes:
                # Same bytes already ingested — skip the duplicate.
                cursor = provider.advance_cursor(
                    current_cursor=cursor, resource=resource
                )
                continue

            # Upload bytes to storage so the ingestion job can read
            # them on a worker without the connector being involved.
            storage_key = generate_storage_key(
                "kb", str(kb.id), resource.filename or resource.resource_id
            )
            await storage.upload(
                storage_key,
                content_bytes,
                resource.mime_type or "application/octet-stream",
            )

            doc = Document(
                knowledge_base_id=kb.id,
                workspace_id=kb.workspace_id,
                filename=resource.filename or "untitled",
                file_path=storage_key,
                file_type=(resource.filename or "").rsplit(".", 1)[-1].lower()
                if "." in (resource.filename or "")
                else "bin",
                file_size=resource.size,
                mime_type=resource.mime_type,
                content_hash=content_hash,
                status="pending",
                processing_phase="queued",
                processing_progress=0,
                data={
                    "source": "connector",
                    "connector_id": str(connector.id),
                    "resource_id": resource.resource_id,
                    **(resource.metadata or {}),
                },
            )
            db.add(doc)
            await db.flush()
            existing_hashes.add(content_hash)

            # Hand off to the regular ingestion pipeline — exactly the
            # same path as a manual upload.
            await enqueue_job(
                db,
                job_type=job_types.JOB_KB_INGEST_DOCUMENT,
                target="backend",
                path=f"{settings.API_PREFIX}/internal/knowledge/ingest",
                payload={"kb_id": str(kb.id), "doc_id": str(doc.id)},
                priority="normal",
                retry={"maxAttempts": 3, "backoffMs": 3_000, "backoffMultiplier": 2},
                idempotency_key=f"kb.ingest:{doc.id}",
                timeout_ms=600_000,
            )

            cursor = provider.advance_cursor(
                current_cursor=cursor, resource=resource
            )
            result.fetched += 1
    except Exception as exc:
        # Hard failure mid-iteration — stamp the error so it surfaces
        # in admin UI. Partial progress (anything ingested before the
        # exception) survives via the cursor advance above.
        logger.exception(
            "connector: hard failure during list_resources for %s", connector.id
        )
        result.errors.append(str(exc)[:500])

    # Finalise the cursor. Provider implementations override
    # ``finalize_cursor`` to add provider-specific keys; the default
    # just stamps last_run_at.
    cursor = provider.finalize_cursor(
        current_cursor=cursor, last_run_at=run_started
    )

    connector.sync_cursor = cursor
    connector.last_sync_at = run_started
    connector.last_error = "; ".join(result.errors)[:8000] if result.errors else None
    result.new_cursor = cursor
    return result
