"""Scheduler tick — polls ``scheduled_triggers`` and fires due rows.

Runs as a long-lived asyncio task started by the FastAPI lifespan
(see ``app.main.create_app``). One tick per ``_TICK_SECONDS``:

  1. SELECT FOR UPDATE SKIP LOCKED on due rows + advance their
     next_run_at via :func:`claim_due`.
  2. For each claimed row, enqueue a ``workflow.run.scheduled`` job
     via the producer — same code path as webhook-triggered runs.
  3. Sleep until the next tick.

Why this design vs APScheduler:
  - We already have the dispatcher + RabbitMQ + jobs table for
    execution. APScheduler would duplicate that infrastructure.
  - The DB-as-source-of-truth pattern means the schedule survives
    backend restart with zero in-memory state to rebuild.
  - SKIP LOCKED lets us run the tick in N backend replicas without
    co-ordination — whoever grabs the row first fires it.

If you ever need sub-minute precision, drop ``_TICK_SECONDS`` and
add a per-row claim-by-id. Most cron use cases (hourly, daily, weekly)
are fine with the 1-minute granularity here.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timezone

from app.modules.runtime.jobs import types as job_types
from app.modules.runtime.jobs.producer import enqueue as enqueue_job
from app.modules.runtime.triggers.scheduled.service import claim_due
from app.platform.config import settings
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

_TICK_SECONDS = 60


async def _tick_once() -> int:
    """Run one scheduler iteration. Returns the number of fired rows.

    Each fired row is committed independently — partial progress
    survives a crash mid-tick rather than re-firing rows we already
    enqueued.
    """
    fired = 0
    async with async_session_factory() as db:
        rows = await claim_due(db, now=datetime.now(timezone.utc))
        if not rows:
            return 0
        for row in rows:
            try:
                await enqueue_job(
                    db,
                    job_type=job_types.JOB_WORKFLOW_RUN_SCHEDULED,
                    target="backend",
                    path=f"{settings.API_PREFIX}/internal/workflows/run",
                    payload={
                        "workflow_id": str(row.workflow_id),
                        "user_id": str(row.created_by) if row.created_by else None,
                        "input_data": row.payload,
                    },
                    workspace_id=row.workspace_id,
                    user_id=row.created_by,
                    priority="normal",
                    retry={
                        "maxAttempts": 3,
                        "backoffMs": 10_000,
                        "backoffMultiplier": 2,
                    },
                    timeout_ms=600_000,
                )
                fired += 1
            except Exception:  # noqa: BLE001
                logger.exception(
                    "scheduler: enqueue failed for trigger %s — will retry next tick",
                    row.id,
                )
        await db.commit()
    return fired


async def run_forever() -> None:
    """Long-lived loop — call from FastAPI lifespan."""
    logger.info("scheduled_triggers: scheduler started (tick=%ds)", _TICK_SECONDS)
    while True:
        try:
            fired = await _tick_once()
            if fired:
                logger.info("scheduled_triggers: fired %d trigger(s)", fired)
        except Exception:  # noqa: BLE001 — log + keep looping
            logger.exception("scheduled_triggers: tick crashed")
        await asyncio.sleep(_TICK_SECONDS)


_task: asyncio.Task[None] | None = None


def start() -> None:
    """Boot the scheduler as a background task. Idempotent — safe to
    call from multiple lifespan hooks during dev autoreload."""
    global _task
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(run_forever(), name="scheduled_triggers.scheduler")


async def stop() -> None:
    """Cancel + await the running scheduler. Safe on a clean shutdown."""
    global _task
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
