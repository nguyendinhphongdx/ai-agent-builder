"""Periodic sweep — fire every active KB connector on a cadence.

Booted from the FastAPI lifespan next to the scheduled_triggers
ticker. One tick per ``_TICK_SECONDS``:

  1. SELECT FOR UPDATE SKIP LOCKED on active connectors whose
     ``last_sync_at`` is older than the cadence (or NULL — never
     synced).
  2. Hand each one to :func:`run_connector` — which iterates +
     ingests + advances the cursor in the same transaction.
  3. Sleep until the next tick.

SKIP LOCKED lets N backend replicas run the loop side-by-side
without re-claiming the same connector.

If a connector takes longer than ``_TICK_SECONDS`` to sync (huge
S3 bucket, slow Notion API), the next tick won't start a second
copy because the first holds the row lock for the duration.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.db.session import async_session_factory
from app.knowledge.connectors.sync import run_connector
from app.models.kb_connector import KBConnector

logger = logging.getLogger("agentforge")

# 1 hour between sweeps. Most connectors care about hour-scale
# freshness; admins who need sooner can hit the manual /sync endpoint.
_TICK_SECONDS = 3600
# Per-connector cadence. NULL last_sync_at = never run, fire on the
# next tick. Otherwise wait at least this long since the last run.
_MIN_SYNC_INTERVAL = timedelta(hours=1)


async def _tick_once() -> int:
    """Returns the number of connectors successfully synced this tick."""
    cutoff = datetime.now(timezone.utc) - _MIN_SYNC_INTERVAL
    synced = 0
    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(KBConnector)
                .where(
                    KBConnector.is_active.is_(True),
                    or_(
                        KBConnector.last_sync_at.is_(None),
                        KBConnector.last_sync_at <= cutoff,
                    ),
                )
                .order_by(KBConnector.last_sync_at.nullsfirst())
                .limit(50)
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
        if not rows:
            return 0
        for row in rows:
            try:
                result = await run_connector(db, row)
                synced += 1
                if result.errors:
                    logger.warning(
                        "connector %s: %d errors in run — %s",
                        row.id,
                        len(result.errors),
                        result.errors[0],
                    )
            except Exception:  # noqa: BLE001
                logger.exception(
                    "connector %s: hard failure during sync — will retry next tick",
                    row.id,
                )
                row.last_error = "scheduler caught uncaught exception"
        await db.commit()
    return synced


async def run_forever() -> None:
    """Long-lived sweep loop."""
    logger.info(
        "kb_connectors: scheduler started (tick=%ds, min_interval=%ds)",
        _TICK_SECONDS,
        int(_MIN_SYNC_INTERVAL.total_seconds()),
    )
    # Tick almost-immediately on startup so a fresh deploy doesn't
    # wait an hour for the first sync.
    while True:
        try:
            n = await _tick_once()
            if n:
                logger.info("kb_connectors: synced %d connector(s)", n)
        except Exception:  # noqa: BLE001
            logger.exception("kb_connectors: tick crashed")
        await asyncio.sleep(_TICK_SECONDS)


_task: asyncio.Task[None] | None = None


def start() -> None:
    global _task
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(run_forever(), name="kb_connectors.scheduler")


async def stop() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
