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


def _client_ip(request: Request) -> str:
    """Resolve the caller's IP, honouring the first hop in X-Forwarded-For.

    We trust the proxy header here because share endpoints are typically
    fronted by a reverse proxy (nginx, Cloudflare). In a no-proxy deploy the
    header will be absent and we fall back to ``request.client.host``.
    """
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_share_rate_limit(request: Request) -> None:
    """Per-IP rate limit for ``/api/share/*`` — anonymous embed widget traffic.

    Mirrors :func:`enforce_external_rate_limit` but keys on client IP rather
    than token id (no auth on the share channel).
    """
    limit = settings.SHARE_RATE_LIMIT_PER_MIN
    if limit <= 0:
        return

    redis = await get_redis()
    if redis is None:
        return

    minute = int(time.time() // 60)
    ip = _client_ip(request)
    key = f"rl:share:{ip}:{minute}"

    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 65)
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("share rate_limit redis incr failed: %s", exc)
        return

    request.state.rate_limit_remaining = max(0, limit - count)

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


# ─── Generic per-route limit (auth + chat + workflow execute, etc.) ──────


async def _bump_counter(key: str, limit: int) -> int | None:
    """Returns the current count after INCR, or None if Redis is unreachable."""
    redis = await get_redis()
    if redis is None:
        return None
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 65)
        return count
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("rate_limit redis incr failed: %s", exc)
        return None


def make_limit(scope: str, limit_per_min: int):
    """Factory: build a FastAPI dependency that limits ``scope`` to ``N/min``.

    Keys per-user when authenticated (request.state.api_token *or* the
    cookie-resolved user). Falls back to client IP when neither is present —
    that's the case for ``/auth/login`` and ``/auth/register`` where there's
    no user yet.

    Use:
        from app.rate_limit import make_limit
        @router.post("/login", dependencies=[Depends(make_limit("auth", 20))])
    """
    async def _enforce(request: Request) -> None:
        if limit_per_min <= 0:
            return

        # Prefer user_id (set by get_current_user). Fall back to api_token id,
        # then client IP for unauthenticated routes.
        from app.context import current_user_id_or_none

        principal: str | None = None
        user_id = current_user_id_or_none()
        if user_id is not None:
            principal = f"u:{user_id}"
        else:
            token = getattr(request.state, "api_token", None)
            if token is not None:
                principal = f"t:{token.id}"
            else:
                principal = f"ip:{_client_ip(request)}"

        minute = int(time.time() // 60)
        key = f"rl:{scope}:{principal}:{minute}"

        count = await _bump_counter(key, limit_per_min)
        if count is None:
            return  # fail-open

        request.state.rate_limit_remaining = max(0, limit_per_min - count)

        if count > limit_per_min:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded ({limit_per_min}/min for {scope}). Retry next minute.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Scope": scope,
                    "X-RateLimit-Limit": str(limit_per_min),
                    "X-RateLimit-Remaining": "0",
                },
            )

    return _enforce
