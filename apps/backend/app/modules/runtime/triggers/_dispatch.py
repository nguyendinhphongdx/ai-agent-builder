"""Shared workflow-run dispatcher.

Every trigger ends the same way: look up the workflow, sanity-check
that it's still active, enqueue a JOB_WORKFLOW_RUN job with a
provider-tagged ``input_data`` envelope. The five legacy services
each inlined ~25 lines of identical-up-to-the-tag boilerplate; this
helper collapses them to one call.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger import Trigger
from app.models.workflow import Workflow
from app.modules.runtime.jobs import types as job_types
from app.modules.runtime.jobs.producer import enqueue as enqueue_job
from app.platform.config import settings

logger = logging.getLogger("agentforge")


async def enqueue_workflow_run(
    db: AsyncSession,
    trigger: Trigger,
    *,
    source_payload: dict[str, Any],
) -> bool:
    """Look up the workflow, check it's active, enqueue a run.

    Returns True iff the run was enqueued. False when the workflow
    is missing or inactive — caller decides whether to surface
    or swallow the no-op.

    Payload envelope shape:
        {
            "workflow_id": "...",
            "user_id":     "...",
            "input_data": {
                "trigger":    "<trigger.type>",
                "trigger_id": "<trigger.id>",
                "<trigger.type>": <source_payload>
            }
        }
    """
    workflow = await db.get(Workflow, trigger.workflow_id)
    if workflow is None or not workflow.is_active:
        return False
    await enqueue_job(
        db,
        job_type=job_types.JOB_WORKFLOW_RUN,
        target="backend",
        path=f"{settings.API_PREFIX}/internal/workflows/run",
        payload={
            "workflow_id": str(workflow.id),
            "user_id": str(workflow.user_id),
            "input_data": {
                "trigger": trigger.type,
                "trigger_id": str(trigger.id),
                trigger.type: source_payload,
            },
        },
        workspace_id=workflow.workspace_id,
        user_id=workflow.user_id,
        priority="normal",
        retry={"maxAttempts": 3, "backoffMs": 5_000, "backoffMultiplier": 2},
        timeout_ms=300_000,
    )
    return True


__all__ = ["enqueue_workflow_run"]
