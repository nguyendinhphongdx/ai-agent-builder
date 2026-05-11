"""Redis-backed idempotency keys for job publishes.

Two layers of dedup:

  1. **Redis SETNX** with TTL — fast path that catches "user clicked
     submit twice" in milliseconds without hitting Postgres.
  2. **`jobs.idempotency_key` UNIQUE** — durable backstop. If the
     Redis key has expired but the job row still exists, the unique
     constraint catches the duplicate at INSERT time.

The producer calls :func:`acquire` before publish. On collision the
caller treats the existing job_id as the answer instead of creating
a new one.

Fail-open: if Redis is down, ``acquire`` returns True (let it
through). The DB unique constraint is the safety net.
"""
from __future__ import annotations

import logging

from app.rate_limit import get_redis

logger = logging.getLogger("agentforge")


# Default TTL matches the longest plausible job duration. A 1-hour
# window covers KB ingestion of large PDFs; longer-running tasks can
# pass their own TTL when calling :func:`acquire`.
_DEFAULT_TTL_SECONDS = 3600


def _redis_key(idempotency_key: str) -> str:
    return f"jobs:idem:{idempotency_key}"


async def acquire(
    idempotency_key: str,
    *,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> bool:
    """Try to reserve ``idempotency_key`` for a new job.

    Returns ``True`` when the key was newly claimed (caller should
    proceed to enqueue). Returns ``False`` when the key already
    exists (caller should look up the prior job and reuse it).

    Fail-open on Redis errors — the durable UNIQUE constraint will
    catch any duplicate that slips through.
    """
    redis = await get_redis()
    if redis is None:
        return True  # Redis disabled — defer to DB unique constraint
    try:
        # NX = set if not exists. Returns True on success, None on collision.
        acquired = await redis.set(
            _redis_key(idempotency_key), "1", nx=True, ex=ttl_seconds
        )
        return bool(acquired)
    except Exception as exc:  # noqa: BLE001 — fail-open on Redis hiccups
        logger.warning("jobs idempotency acquire failed: %s", exc)
        return True


async def release(idempotency_key: str) -> None:
    """Drop the Redis key — called after a job reaches a terminal
    state so the same idempotency token can be reused later (rare,
    but supports legitimate "retry the whole operation after fix"
    flows). DB row's unique constraint still prevents double-publish
    on the same in-flight key."""
    redis = await get_redis()
    if redis is None:
        return
    try:
        await redis.delete(_redis_key(idempotency_key))
    except Exception as exc:  # noqa: BLE001
        logger.warning("jobs idempotency release failed: %s", exc)
