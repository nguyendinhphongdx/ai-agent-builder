"""Async background loops booted by the FastAPI lifespan.

Each module here exposes the same minimal contract:
  * ``start() -> None``     — spawns its ``asyncio.Task``. Idempotent.
  * ``async stop() -> None`` — cancels + awaits the task. Idempotent.

That uniformity lets ``app.main`` register new loops by appending to
the :data:`WORKERS` list below — no per-module hook to invent each time.

Why gather them here:
  * one place to audit "what's running in the API process"
  * lifespan stays a single ``for w in WORKERS`` loop instead of a
    fan-out of explicit ``start()`` / ``stop()`` calls that drifts
    every time someone adds a new background module
  * keeps feature folders focused on request-time behavior

What lives here:
  * audit_purge        — daily retention sweep for audit_logs
  * billing_reporter   — 15-min Stripe metered-usage flush
  * kb_sync            — periodic KB connector sweep
  * email_poll         — IMAP poll worker for email triggers
  * scheduled_triggers — cron / interval triggers ticker

Adding a new worker:
  1. Drop a module here that exposes ``start()`` + ``async stop()``.
  2. Append it to :data:`WORKERS` below.
The lifespan picks it up on next boot.
"""

from __future__ import annotations

from typing import Protocol

from app.background import (
    audit_purge,
    billing_reporter,
    email_poll,
    kb_sync,
    scheduled_triggers,
)


class BackgroundWorker(Protocol):
    """Structural type satisfied by every module in this package."""

    def start(self) -> None: ...

    async def stop(self) -> None: ...


# Boot order matters: `scheduled_triggers` first so cron-fired runs are
# already being scheduled when other workers come up; `email_poll` last
# since it's the chattiest and tolerates a slight start delay.
WORKERS: list[BackgroundWorker] = [
    scheduled_triggers,
    audit_purge,
    kb_sync,
    billing_reporter,
    email_poll,
]
