"""Internal workflow runner — invoked by dispatcher consumer.

Webhook `immediately` mode and (eventually) cron triggers enqueue
through ``app.jobs.producer.enqueue`` which POSTs here. The job_id
in the body lets us walk the Job row through its lifecycle.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.jobs import service as job_service
from app.models.workflow import Workflow

logger = logging.getLogger("agentforge")
router = APIRouter(prefix="/workflows", tags=["internal:workflows"])


class WorkflowRunRequest(BaseModel):
    workflow_id: uuid.UUID
    user_id: uuid.UUID
    input_data: dict[str, Any] = {}
    job_id: uuid.UUID | None = None


@router.post("/run")
async def run_workflow_endpoint(
    body: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Execute a workflow asynchronously. Marks the Job row through
    running → completed/dead so the dashboard reflects state."""
    job = await job_service.get_job(db, body.job_id) if body.job_id else None

    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == body.workflow_id)
    )
    workflow = result.scalar_one_or_none()
    if workflow is None:
        if job is not None:
            await job_service.mark_dead(db, job, error="workflow not found")
            await db.commit()
        return {"status": "skipped", "reason": "workflow not found"}

    if job is not None:
        await job_service.mark_running(db, job)
        await db.commit()

    try:
        from app.workflows.runner import WorkflowRunner

        runner = WorkflowRunner(db)
        run = await runner.run(
            workflow=workflow,
            user_id=body.user_id,
            input_data=body.input_data,
        )
        await db.commit()
    except Exception as exc:
        logger.exception("workflow.run failed for workflow=%s", body.workflow_id)
        if job is not None:
            terminal = job.attempt >= job.max_attempts
            if terminal:
                await job_service.mark_dead(db, job, error=str(exc))
            else:
                await job_service.mark_failed(db, job, error=str(exc))
            await db.commit()
        raise

    if job is not None:
        await job_service.mark_completed(
            db,
            job,
            result={"run_id": str(run.id), "status": run.status},
        )
        await db.commit()

    return {"run_id": str(run.id), "status": run.status}
