"""Long-lived IMAP poll worker for email triggers.

Single async loop, sleeps 30s between sweeps. Each sweep finds
every active trigger whose ``last_polled_at`` is older than its
``poll_interval_seconds`` and runs ``poll_once`` on it. Per-row
cadence is enforced in SQL so the loop frequency doesn't dictate
the user-facing freshness.

Why one loop and not a worker pool: a typical deployment will
have <100 email triggers; IMAP fetches are I/O bound and yield
back during ``asyncio.to_thread``. Move to a queue when this
becomes a hotspot.

Disabled implicitly when no triggers exist — the sweep does no
work but also no harm.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_trigger import EmailTrigger
from app.modules.runtime.triggers.email.service import poll_once
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

_SWEEP_INTERVAL_SECONDS = 30
_INITIAL_DELAY_SECONDS = 30


async def _due_triggers(db: AsyncSession) -> list[EmailTrigger]:
    now = datetime.now(timezone.utc)
    stmt = select(EmailTrigger).where(EmailTrigger.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    out: list[EmailTrigger] = []
    for row in rows:
        if row.last_polled_at is None:
            out.append(row)
            continue
        if row.last_polled_at + timedelta(
            seconds=row.poll_interval_seconds
        ) <= now:
            out.append(row)
    return out


async def _sweep_once() -> int:
    """One sweep — returns the total number of messages dispatched."""
    total = 0
    async with async_session_factory() as db:
        triggers = await _due_triggers(db)
        for trigger in triggers:
            try:
                total += await poll_once(db, trigger)
            except Exception:  # noqa: BLE001
                logger.exception(
                    "email_trigger %s: sweep crashed", trigger.id
                )
                await db.rollback()
                continue
            await db.commit()
    return total


async def run_forever() -> None:
    logger.info(
        "email_triggers.scheduler: started (cadence=%ds)",
        _SWEEP_INTERVAL_SECONDS,
    )
    await asyncio.sleep(_INITIAL_DELAY_SECONDS)

    while True:
        try:
            dispatched = await _sweep_once()
            if dispatched:
                logger.info(
                    "email_triggers.scheduler: dispatched %d messages",
                    dispatched,
                )
        except Exception:  # noqa: BLE001
            logger.exception("email_triggers.scheduler: sweep crashed")
        await asyncio.sleep(_SWEEP_INTERVAL_SECONDS)


_task: asyncio.Task[None] | None = None


def start() -> None:
    global _task
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(run_forever(), name="email_triggers.scheduler")


async def stop() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
