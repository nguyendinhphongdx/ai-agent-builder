"""Async background loops booted by the FastAPI lifespan.

Each module here exposes the same minimal contract:
  * ``start() -> None``     — spawns its ``asyncio.Task``. Idempotent.
  * ``async stop() -> None`` — cancels + awaits the task. Idempotent.

That uniformity lets ``app.main`` register new loops without
inventing a per-module hook each time.

Why gather them here:
  * one place to audit "what's running in the API process"
  * lifespan import list stays a flat fan-out instead of digging
    into 5 different feature folders to learn what background
    work the app does
  * keeps feature folders focused on request-time behavior

What lives here:
  * audit_purge        — daily retention sweep for audit_logs
  * billing_reporter   — 15-min Stripe metered-usage flush
  * kb_sync            — periodic KB connector sweep
  * email_poll         — IMAP poll worker for email triggers
  * scheduled_triggers — cron / interval triggers ticker
"""
