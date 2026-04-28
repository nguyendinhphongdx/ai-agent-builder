"""Per-token rate limit for the public ``/api/external/*`` API.

Implementation: fixed-window counter in Redis. Cheaper than sliding-window
(one INCR + EXPIRE per request) and good enough for the protection we need —
the slight burst tolerance at minute boundaries is acceptable.

Cookie-auth requests bypass entirely: ``request.state.api_token`` is None
when :func:`get_current_user` resolved a session cookie.
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from app.config import settings

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger("agentforge")

_redis_client: "Redis | None" = None


async def get_redis() -> "Redis | None":
    """Lazy singleton Redis client. Returns None when REDIS_URL is unset."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not settings.REDIS_URL:
        return None
    from redis.asyncio import Redis

    _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def enforce_external_rate_limit(request: Request) -> None:
    """FastAPI dependency — reject when the caller's token exceeds its quota.

    No-op when:
      - the request is cookie-auth (no api_token in state),
      - rate limiting is disabled (limit ≤ 0 or REDIS_URL unset),
      - Redis is unreachable (we fail-open rather than block traffic).
    """
    token = getattr(request.state, "api_token", None)
    if token is None:
        return

    limit = settings.EXTERNAL_RATE_LIMIT_PER_MIN
    if limit <= 0:
        return

    redis = await get_redis()
    if redis is None:
        return

    minute = int(time.time() // 60)
    key = f"rl:ext:{token.id}:{minute}"

    try:
        count = await redis.incr(key)
        if count == 1:
            # Set TTL only on first increment so the key auto-expires once
            # the window passes. +5s grace covers clock skew between replicas.
            await redis.expire(key, 65)
    except Exception as exc:  # noqa: BLE001 — fail-open on Redis hiccups
        logger.warning("rate_limit redis incr failed: %s", exc)
        return

    remaining = max(0, limit - count)
    request.state.rate_limit_remaining = remaining

    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded ({limit}/min). Retry next minute.",
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
