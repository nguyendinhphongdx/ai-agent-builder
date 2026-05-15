"""Per-account login lockout to slow credential stuffing.

The existing ``AUTH_PUBLIC_LIMIT`` (30/min per IP across all public
auth routes) catches an obvious flood from one address but does
nothing for an attacker who rotates IPs while hammering one email —
each request lands in a different bucket and the per-IP counter
never fires.

This module adds a complementary per-email counter:

  - record_failed_login(email)  on every bad password
  - is_locked(email)            short-circuits login before the bcrypt
                                compare, so failed attempts after the
                                threshold are O(redis) cheap
  - clear_failures(email)       wipes the counter on successful auth

Threshold + TTL come from settings so an operator can tighten them
without a deploy if they spot stuffing in the audit log.

DoS trade-off: yes, a stranger who knows your email could lock you
out for ``LOCKOUT_TTL_SECONDS`` by submitting wrong passwords. The
mitigation is the short window (15 min default) and the fact that a
real user can always wait or contact support. Industry standard:
Auth0, Cognito, Okta all do per-account lockout for exactly this
reason — slowing the attacker is worth the rare annoyance.

Redis-only: when REDIS_URL is unset (single-process dev) lockout is
a no-op so local development keeps flowing.
"""
from __future__ import annotations

import logging

from app.platform.config import settings
from app.platform.rate_limit import get_redis

logger = logging.getLogger("agentforge")


def _key(email: str) -> str:
    # Lowercase so "User@Example.com" and "user@example.com" share a bucket.
    return f"auth:lockout:{email.strip().lower()}"


async def is_locked(email: str) -> bool:
    """True iff the email has crossed the lockout threshold.

    Fail-open on Redis errors — security matters but we don't want a
    Redis outage to lock every customer out of their own product.
    """
    threshold = settings.LOGIN_LOCKOUT_THRESHOLD
    if threshold <= 0:
        return False
    redis = await get_redis()
    if redis is None:
        return False
    try:
        raw = await redis.get(_key(email))
    except Exception as exc:  # noqa: BLE001 — fail-open
        logger.warning("lockout: redis get failed: %s", exc)
        return False
    return raw is not None and int(raw) >= threshold


async def record_failed_login(email: str) -> int:
    """INCR the per-email counter and return the new value.

    First failure sets the TTL — subsequent INCRs within the window
    don't reset it, so the lock-out clock starts from the *first*
    bad attempt, not the latest. That stops a slow attacker from
    keeping the bucket alive indefinitely.

    Returns ``0`` when Redis is unavailable (no lockout possible).
    """
    threshold = settings.LOGIN_LOCKOUT_THRESHOLD
    if threshold <= 0:
        return 0
    redis = await get_redis()
    if redis is None:
        return 0
    key = _key(email)
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, settings.LOGIN_LOCKOUT_TTL_SECONDS)
        return int(count)
    except Exception as exc:  # noqa: BLE001
        logger.warning("lockout: redis incr failed: %s", exc)
        return 0


async def clear_failures(email: str) -> None:
    """Reset the counter — called on successful auth so a user who
    typed their password wrong twice then got it right doesn't carry
    the bad-attempts state forward.
    """
    redis = await get_redis()
    if redis is None:
        return
    try:
        await redis.delete(_key(email))
    except Exception as exc:  # noqa: BLE001
        logger.warning("lockout: redis del failed: %s", exc)


__all__ = ["is_locked", "record_failed_login", "clear_failures"]
