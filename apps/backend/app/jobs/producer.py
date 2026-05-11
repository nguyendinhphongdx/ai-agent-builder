"""Higher-level enqueue API on top of the dispatcher client.

What this adds over raw ``dispatcher.enqueue``:

  - **Idempotency**: Redis SETNX fast-path + ``jobs.idempotency_key``
    UNIQUE constraint durable backstop. Callers can pass the same
    key twice and get back the existing job instead of double-publish.
  - **Status tracking**: every publish gets a ``Job`` row that the
    consumer flips through queued → running → completed/dead. The
    UI polls this row instead of asking RabbitMQ directly.
  - **Tenant tagging**: workspace_id + user_id are auto-stamped
    from request context so DLQ admin views can filter by tenant.

Callers should use :func:`enqueue` rather than the raw dispatcher
client for any task they want visible in the dashboard.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dispatcher_client import (
    DispatcherClient,
    Priority,
    ServiceName,
    HttpMethod,
    RetryConfig,
)
from app.jobs import idempotency, service as job_service
from app.models.job import Job

logger = logging.getLogger("agentforge")


# Lazy singleton — built on first use so tests can monkeypatch the
# dispatcher URL/secret via settings before the client materialises.
_dispatcher: DispatcherClient | None = None


def _get_dispatcher() -> DispatcherClient:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = DispatcherClient(
            base_url=settings.DISPATCHER_URL,
            secret=settings.DISPATCHER_SECRET or None,
        )
    return _dispatcher


@dataclass(frozen=True)
class EnqueueResult:
    """What :func:`enqueue` returns. ``deduped`` is True when the
    caller hit an existing idempotency_key — they got back the
    in-flight job instead of a fresh publish."""

    job: Job
    deduped: bool


async def enqueue(
    db: AsyncSession,
    *,
    job_type: str,
    target: ServiceName,
    path: str,
    payload: dict[str, Any],
    method: HttpMethod = "POST",
    headers: dict[str, str] | None = None,
    priority: Priority = "normal",
    retry: RetryConfig | None = None,
    idempotency_key: str | None = None,
    max_attempts: int = 5,
    timeout_ms: int = 30_000,
    workspace_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> EnqueueResult:
    """Publish a job to the dispatcher with full tracking.

    Steps:
      1. If ``idempotency_key`` set, try Redis SETNX. On collision,
         look up the existing Job row and return it as ``deduped``.
      2. INSERT a ``queued`` Job row (UNIQUE on idempotency_key
         catches the rare case where Redis lost the key but the row
         survives).
      3. Forward the payload + ``job_id`` to dispatcher's
         ``/dispatch/internal``. The consumer (target service) gets
         the job_id in the request body and uses it to call
         ``mark_running``/``mark_completed`` back here.
      4. Pin the dispatcher's messageId on the Job row.

    On dispatcher publish failure the Job stays in ``queued`` and
    the caller decides whether to retry or surface to user.
    """
    # ── Idempotency fast-path ────────────────────────────────────
    if idempotency_key is not None:
        acquired = await idempotency.acquire(idempotency_key)
        if not acquired:
            existing = await job_service.get_job_by_idempotency_key(db, idempotency_key)
            if existing is not None:
                return EnqueueResult(job=existing, deduped=True)
            # Redis says taken but row not found — odd state, fall through
            # to INSERT and let UNIQUE constraint catch any race.

    # ── Job row ──────────────────────────────────────────────────
    try:
        job = await job_service.create_job(
            db,
            job_type=job_type,
            payload=payload,
            idempotency_key=idempotency_key,
            max_attempts=max_attempts,
            workspace_id=workspace_id,
            user_id=user_id,
        )
    except IntegrityError:
        # UNIQUE collision on idempotency_key — race between SETNX and
        # the actual INSERT. Roll back + return the winning row.
        await db.rollback()
        if idempotency_key is not None:
            existing = await job_service.get_job_by_idempotency_key(db, idempotency_key)
            if existing is not None:
                return EnqueueResult(job=existing, deduped=True)
        raise  # Genuine integrity error — don't swallow.

    # ── Dispatcher publish ───────────────────────────────────────
    # We forward `job_id` in the body so the consumer can call back
    # to update status. The dispatcher itself doesn't interpret it.
    body_with_meta = {**payload, "job_id": str(job.id)}
    resp = await _get_dispatcher().enqueue(
        target=target,
        path=path,
        method=method,
        body=body_with_meta,
        headers=headers,
        priority=priority,
        retry=retry,
        event=job_type,
        timeout_ms=timeout_ms,
        correlation_id=str(job.id),
    )
    if resp.get("success") and resp.get("messageId"):
        await job_service.set_dispatcher_message_id(db, job, resp["messageId"])
    else:
        logger.warning(
            "dispatcher publish failed for job %s (%s); row stays queued",
            job.id,
            job_type,
        )

    return EnqueueResult(job=job, deduped=False)
