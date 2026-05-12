"""Daily retention sweep for audit_logs.

Runs as a long-lived asyncio task booted from the FastAPI lifespan
(alongside the scheduled_triggers tick). Sleeps 24h between sweeps —
audit purge isn't time-sensitive, and we want to avoid scanning the
table more often than needed.

Disabled when ``AUDIT_LOG_RETENTION_DAYS = 0``.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from app.modules.audit.service import purge_older_than
from app.platform.config import settings
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

# 24h cadence. Skew the first run by ~5 min so backend startup doesn't
# pile a slow DELETE on top of every other init-time query.
_SWEEP_INTERVAL_SECONDS = 24 * 60 * 60
_INITIAL_DELAY_SECONDS = 5 * 60


async def _sweep_once(retention_days: int) -> int:
    async with async_session_factory() as db:
        deleted = await purge_older_than(db, days=retention_days)
        return deleted


async def run_forever() -> None:
    """Long-lived purge loop."""
    retention_days = settings.AUDIT_LOG_RETENTION_DAYS
    if retention_days <= 0:
        logger.info("audit.purge: disabled (AUDIT_LOG_RETENTION_DAYS=0)")
        return

    logger.info(
        "audit.purge: started (retention=%dd, cadence=%ds)",
        retention_days,
        _SWEEP_INTERVAL_SECONDS,
    )
    # Initial delay so startup-time DDL/migrations don't compete.
    await asyncio.sleep(_INITIAL_DELAY_SECONDS)

    while True:
        try:
            deleted = await _sweep_once(retention_days)
            if deleted:
                logger.info("audit.purge: removed %d rows older than %dd", deleted, retention_days)
        except Exception:  # noqa: BLE001
            logger.exception("audit.purge: sweep crashed — will retry next interval")
        await asyncio.sleep(_SWEEP_INTERVAL_SECONDS)


_task: asyncio.Task[None] | None = None


def start() -> None:
    """Boot the purge loop. Idempotent."""
    global _task
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(run_forever(), name="audit.purge")


async def stop() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
