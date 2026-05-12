"""Liveness + readiness probes.

- ``/healthz`` — liveness. Returns 200 as long as the process is up.
  Mounted at the root, not under ``/api``, so infra (k8s, ALB target
  groups, uptime monitors) hits it without API-prefix awareness.

- ``/readyz`` — readiness. Pings the dependencies that must be reachable
  for the backend to serve real traffic: Postgres + (optional) Redis.
  503 when any required dep is unreachable so the orchestrator pulls
  the pod out of rotation instead of routing failing requests at it.

Both probes skip auth + CORS (mounted before any router that requires
them, and FastAPI's exception handler still produces JSON if Postgres
errors out under us).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.platform.config import settings
from app.platform.db.session import async_session_factory

router = APIRouter(tags=["health"])


@router.get("/healthz", include_in_schema=False)
async def liveness() -> dict[str, str]:
    """Liveness — succeeds if the process is responsive."""
    return {"status": "ok"}


async def _ping_db(timeout: float = 1.5) -> tuple[bool, str | None]:
    try:
        async with async_session_factory() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=timeout)
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


async def _ping_redis(timeout: float = 1.0) -> tuple[bool, str | None]:
    if not settings.REDIS_URL:
        # Redis is optional (rate limiting only). Treat as healthy.
        return True, None
    try:
        from redis.asyncio import Redis

        client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await asyncio.wait_for(client.ping(), timeout=timeout)
        finally:
            await client.aclose()
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


@router.get("/readyz", include_in_schema=False)
async def readiness() -> JSONResponse:
    """Readiness — succeeds when DB and Redis (if configured) are reachable."""
    db_ok, db_err = await _ping_db()
    redis_ok, redis_err = await _ping_redis()

    body = {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "checks": {
            "database": "ok" if db_ok else f"fail: {db_err}",
            "redis": "ok" if redis_ok else f"fail: {redis_err}",
        },
    }
    code = 200 if (db_ok and redis_ok) else 503
    return JSONResponse(content=body, status_code=code)
