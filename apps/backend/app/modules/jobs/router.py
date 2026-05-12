"""User-facing /api/jobs endpoints — list + status polling.

Workspace-scoped: callers see only jobs they own (created in the
active workspace, or system jobs without a workspace_id are hidden).
Admin DLQ surface lives at /api/admin/jobs.

Used by:
  - upload UI polling KB ingestion progress
  - workflow run history page
  - any future feature that needs "is this background task done yet?"
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.jobs.types import ALL_JOB_TYPES
from app.platform.context import current_workspace_id_or_none
from app.platform.db.session import get_db

router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    dependencies=[Depends(get_current_user)],
)


class JobRow(BaseModel):
    """Caller-facing job shape — drops dispatcher_message_id and
    payload (those are ops detail)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: str
    attempt: int
    max_attempts: int
    error: str | None
    result: dict[str, Any] | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


@router.get("", response_model=list[JobRow])
async def list_my_jobs_endpoint(
    job_type: str | None = Query(None, description="Filter by job_type."),
    status: str | None = Query(None, description="Filter by status."),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List jobs the caller can see — own user_id OR within the
    active workspace. Sorted newest first."""
    workspace_id = current_workspace_id_or_none()

    stmt = (
        select(Job)
        .where(Job.user_id == current_user.id)
        .order_by(Job.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if workspace_id is not None:
        stmt = stmt.where(Job.workspace_id == workspace_id)
    if job_type:
        if job_type not in ALL_JOB_TYPES:
            raise HTTPException(400, detail=f"Unknown job_type: {job_type}")
        stmt = stmt.where(Job.job_type == job_type)
    if status:
        stmt = stmt.where(Job.status == status)

    rows = (await db.execute(stmt)).scalars().all()
    return [JobRow.model_validate(r) for r in rows]


@router.get("/{job_id}", response_model=JobRow)
async def get_my_job_endpoint(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll a single job's status. 404 if the job doesn't exist or
    isn't owned by the caller — opaque on purpose so cross-tenant
    job ids don't leak existence."""
    workspace_id = current_workspace_id_or_none()
    stmt = select(Job).where(Job.id == job_id, Job.user_id == current_user.id)
    if workspace_id is not None:
        stmt = stmt.where(Job.workspace_id == workspace_id)
    job = await db.scalar(stmt)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobRow.model_validate(job)
