"""Scheduled (cron) handler — :class:`PollingTrigger` implementation.

The heavy lifting (cron parsing, ``claim_due``, ``sync_from_workflow``)
lives in :mod:`scheduled.service` because workflow-save logic + the
background loop import it directly. The handler is the thin
abstraction layer wiring it into the registry.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger import TRIGGER_TYPE_SCHEDULED, Trigger
from app.modules.runtime.triggers._base import PollingTrigger
from app.modules.runtime.triggers._dispatch import enqueue_workflow_run
from app.modules.runtime.triggers.schemas import ScheduledConfig


class ScheduledHandler(PollingTrigger):
    type = TRIGGER_TYPE_SCHEDULED
    label = "Scheduled (cron)"
    config_schema = ScheduledConfig
    # Cron triggers carry a static fire payload in ``config.payload``
    # — no per-trigger Fernet secret needed.
    credentials_schema = None

    async def tick(self, db: AsyncSession, trigger: Trigger) -> int:
        """Dispatch one workflow run for a row whose ``next_run_at``
        has fired. The caller (``app.background.scheduled_triggers``)
        already advanced ``next_run_at`` via ``claim_due`` before
        invoking this, so we only handle the dispatch side.

        Returns 1 on dispatch, 0 if the workflow disappeared mid-flight.
        """
        payload = (trigger.config or {}).get("payload") or {}
        ok = await enqueue_workflow_run(db, trigger, source_payload=payload)
        if ok:
            trigger.last_fired_at = datetime.now(timezone.utc)
            await db.flush()
            return 1
        return 0


__all__ = ["ScheduledHandler"]
