"""Connector sync orchestration.

One entry point — :func:`run_connector(db, connector)` — that:
  1. Resolves the provider via the registry.
  2. Decrypts credentials.
  3. Iterates the provider's resources.
  4. Per-resource: dedupes against existing Documents by
     content_hash, persists a new Document row, hands it off to
     the existing KB ingestion pipeline via the jobs queue.
  5. Advances + persists the cursor.

The orchestrator is provider-agnostic — adding a new connector
needs zero changes here.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.jobs import types as job_types
from app.jobs.producer import enqueue as enqueue_job
from app.knowledge.connectors import (
    KBConnectorRunResult,
    build_connector,
)
from app.knowledge.service import get_knowledge_base_unscoped
from app.models.document import Document
from app.models.kb_connector import KBConnector as KBConnectorRow
from app.security.crypto import decrypt_secret
from app.storage import generate_storage_key, get_storage

logger = logging.getLogger("agentforge")


def _decrypt_credentials(encrypted: str | None) -> dict | None:
    if not encrypted:
        return None
    try:
        return json.loads(decrypt_secret(encrypted))
    except (ValueError, json.JSONDecodeError):
        logger.exception("connector: failed to decrypt credentials blob")
        return None


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
