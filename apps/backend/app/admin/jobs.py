"""Admin DLQ inspector — list, view, replay, delete failed jobs.

Mounted on the moderator-gated /api/admin router. Cross-tenant by
design: ops need to triage failures regardless of which workspace
they belong to. Per-workspace status polling lives at /api/jobs
(Block 4).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db
from app.dispatcher_client import DispatcherClient
from app.jobs import service as job_service
from app.jobs.types import ALL_JOB_TYPES
from app.models.job import (
    JOB_STATUS_DEAD,
    JOB_STATUS_FAILED,
    Job,
)

router = APIRouter(prefix="/jobs", tags=["admin:jobs"])


# ─── Schemas ───────────────────────────────────────────────────────


class AdminJobRow(BaseModel):
    """Compact row shape for the list view."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID | None
    user_id: uuid.UUID | None
    job_type: str
    status: str
    attempt: int
    max_attempts: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class AdminJobDetail(AdminJobRow):
    """Full detail — adds payload/result/dispatcher_message_id."""

    idempotency_key: str | None
    payload: dict
    result: dict | None
    dispatcher_message_id: str | None


# ─── List + filter ─────────────────────────────────────────────────


@router.get("", response_model=list[AdminJobRow])
async def list_jobs_endpoint(
    status: str | None = Query(
        None,
        description="Filter by status. Default returns dead+failed (DLQ view).",
    ),
    job_type: str | None = Query(None, description="Filter by job_type."),
    workspace_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job).order_by(Job.created_at.desc()).offset(offset).limit(limit)

    if status is None:
        # Default DLQ view — anything not currently healthy.
        stmt = stmt.where(Job.status.in_([JOB_STATUS_DEAD, JOB_STATUS_FAILED]))
    else:
        stmt = stmt.where(Job.status == status)

    if job_type:
        if job_type not in ALL_JOB_TYPES:
            raise HTTPException(
                status_code=400, detail=f"Unknown job_type: {job_type}"
            )
        stmt = stmt.where(Job.job_type == job_type)

    if workspace_id is not None:
        stmt = stmt.where(Job.workspace_id == workspace_id)

    rows = (await db.execute(stmt)).scalars().all()
    return [AdminJobRow.model_validate(r) for r in rows]


# ─── Counts (for DLQ badge in the admin UI) ────────────────────────


class JobsCounts(BaseModel):
    queued: int
    running: int
    failed: int
    dead: int
    completed: int


@router.get("/counts", response_model=JobsCounts)
async def jobs_counts_endpoint(db: AsyncSession = Depends(get_db)) -> JobsCounts:
    """Aggregate counts by status — drives the admin sidebar badge."""
    rows = (
        await db.execute(
            select(Job.status, func.count())
            .group_by(Job.status)
        )
    ).all()
    counts = {status: int(n) for status, n in rows}
    return JobsCounts(
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        failed=counts.get("failed", 0),
        dead=counts.get("dead", 0),
        completed=counts.get("completed", 0),
    )


# ─── Detail ────────────────────────────────────────────────────────


@router.get("/{job_id}", response_model=AdminJobDetail)
async def get_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return AdminJobDetail.model_validate(job)


# ─── Replay ────────────────────────────────────────────────────────


_dispatcher: DispatcherClient | None = None


def _get_dispatcher() -> DispatcherClient:
    """Lazy singleton so settings can be patched before client builds."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = DispatcherClient(
            base_url=settings.DISPATCHER_URL,
            secret=settings.DISPATCHER_SECRET or None,
        )
    return _dispatcher


# Map JOB_KB_INGEST_DOCUMENT etc. back to (target, path) for replay.
# Keep this in sync with the producers — adding a new job_type that
# isn't replayable here means it can't be retried from the admin UI.
_REPLAY_ROUTES: dict[str, tuple[str, str]] = {
    "kb.ingest.document": ("backend", f"{settings.API_PREFIX}/internal/knowledge/ingest"),
    "workflow.run": ("backend", f"{settings.API_PREFIX}/internal/workflows/run"),
}


@router.post("/{job_id}/replay", response_model=AdminJobDetail)
async def replay_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Re-enqueue a dead/failed job. Resets status to ``queued`` and
    re-publishes the original payload to the dispatcher.

    Attempt counter is preserved — replay doesn't refund retries.
    Use this when you've fixed the underlying cause (DB outage,
    bad credentials, …) and want to redrive the queued work."""
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    route = _REPLAY_ROUTES.get(job.job_type)
    if route is None:
        raise HTTPException(
            status_code=400,
            detail=f"job_type {job.job_type!r} has no replay route registered",
        )
    target, path = route

    # Reset state first so a fast failure leaves the job back in
    # ``queued`` (consumer will flip it again on pick up).
    await job_service.requeue(db, job)
    await db.commit()

    body_with_meta = {**job.payload, "job_id": str(job.id)}
    resp = await _get_dispatcher().enqueue(
        target=target,  # type: ignore[arg-type]
        path=path,
        body=body_with_meta,
        event=job.job_type,
        correlation_id=str(job.id),
        timeout_ms=600_000,
    )
    if resp.get("success") and resp.get("messageId"):
        await job_service.set_dispatcher_message_id(db, job, resp["messageId"])
        await db.commit()
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Dispatcher publish failed; job left in queued state",
        )

    await db.refresh(job)
    return AdminJobDetail.model_validate(job)


# ─── Delete ────────────────────────────────────────────────────────


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Hard-delete a job row. Use for DLQ cleanup once you've decided
    a failed job is permanently abandoned (e.g. deleted KB, removed
    workspace). Doesn't touch the RabbitMQ queue — that's a separate
    DLQ purge."""
    job = await job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()
