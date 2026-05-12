"""CRUD + lifecycle for the ``jobs`` table.

The transitions are intentionally narrow: callers can ``mark_running``,
``mark_completed``, ``mark_failed``, or ``mark_dead`` — no free-form
status writes. Keeps the state machine honest.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_DEAD,
    JOB_STATUS_FAILED,
    JOB_STATUS_QUEUED,
    JOB_STATUS_RUNNING,
    Job,
)
from app.platform.context import current_user_id_or_none, current_workspace_id_or_none


async def create_job(
    db: AsyncSession,
    *,
    job_type: str,
    payload: dict,
    idempotency_key: str | None = None,
    max_attempts: int = 5,
    workspace_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> Job:
    """Insert a new ``queued`` job row.

    Tenant + actor default to the current request context — pass
    explicit values when enqueuing from a non-request scope (CLI,
    cron tick, webhook).
    """
    job = Job(
        workspace_id=workspace_id if workspace_id is not None else current_workspace_id_or_none(),
        user_id=user_id if user_id is not None else current_user_id_or_none(),
        job_type=job_type,
        idempotency_key=idempotency_key,
        status=JOB_STATUS_QUEUED,
        payload=payload,
        max_attempts=max_attempts,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await db.scalar(select(Job).where(Job.id == job_id))


async def get_job_by_idempotency_key(
    db: AsyncSession, idempotency_key: str
) -> Job | None:
    return await db.scalar(
        select(Job).where(Job.idempotency_key == idempotency_key)
    )


async def set_dispatcher_message_id(
    db: AsyncSession, job: Job, message_id: str
) -> None:
    """Pin the RabbitMQ message id after a successful publish."""
    job.dispatcher_message_id = message_id
    await db.flush()


async def mark_running(db: AsyncSession, job: Job) -> Job:
    """Consumer entry — mark the job as picked up + bump attempt."""
    job.status = JOB_STATUS_RUNNING
    job.attempt = (job.attempt or 0) + 1
    job.started_at = datetime.now(timezone.utc)
    await db.flush()
    return job


async def mark_completed(
    db: AsyncSession, job: Job, *, result: dict | None = None
) -> Job:
    """Terminal success state."""
    job.status = JOB_STATUS_COMPLETED
    job.result = result
    job.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return job


async def mark_failed(
    db: AsyncSession, job: Job, *, error: str
) -> Job:
    """Retryable failure — stays in ``failed`` until the worker
    re-enqueues (which flips it back to ``queued``) or the dispatcher
    pushes it to DLQ (caller switches to :func:`mark_dead`)."""
    job.status = JOB_STATUS_FAILED
    job.error = error[:8000]  # bound the payload — TEXT column but logs get huge
    await db.flush()
    return job


async def mark_dead(db: AsyncSession, job: Job, *, error: str) -> Job:
    """Terminal failure — max_attempts exhausted. Visible in the
    admin DLQ view."""
    job.status = JOB_STATUS_DEAD
    job.error = error[:8000]
    job.completed_at = datetime.now(timezone.utc)
    await db.flush()
    return job


async def requeue(db: AsyncSession, job: Job) -> Job:
    """Admin replay — reset the job to ``queued`` so the dispatcher
    consumer picks it up again. Resets error + completed_at; preserves
    attempt counter (retries don't reset the budget)."""
    job.status = JOB_STATUS_QUEUED
    job.error = None
    job.completed_at = None
    await db.flush()
    return job
