"""One-shot auth-token helpers — email verification & password reset.

Token lifecycle:
    create_and_store(user_id, purpose) -> plaintext_token
        └─ we email/link the plaintext to the user
    redeem(plaintext_token, purpose) -> user_id
        └─ validates expiry, marks used_at
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_token import (
    PURPOSE_EMAIL_CHANGE,
    PURPOSE_EMAIL_VERIFICATION,
    PURPOSE_PASSWORD_RESET,
    AuthToken,
)

__all__ = [
    "PURPOSE_EMAIL_CHANGE",
    "PURPOSE_EMAIL_VERIFICATION",
    "PURPOSE_PASSWORD_RESET",
    "create_and_store",
    "create_numeric_code",
    "redeem",
    "invalidate_unused",
]


def _hash(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def invalidate_unused(
    db: AsyncSession,
    user_id: uuid.UUID,
    purpose: str,
) -> None:
    """Mark every prior, unused token of this purpose for this user as used.

    Ensures only the latest issued link is redeemable.
    """
    await db.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user_id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )


async def create_and_store(
    db: AsyncSession,
    user_id: uuid.UUID,
    purpose: str,
    ttl: timedelta,
) -> str:
    """Create a fresh long URL-safe token. Used for magic-link flows.

    The plaintext is never stored — caller is responsible for delivering it
    (e.g. via email) since it cannot be recovered later.
    """
    await invalidate_unused(db, user_id, purpose)

    plaintext = secrets.token_urlsafe(32)
    token = AuthToken(
        user_id=user_id,
        token_hash=_hash(plaintext),
        purpose=purpose,
        expires_at=_now() + ttl,
        created_at=_now(),
    )
    db.add(token)
    await db.flush()
    return plaintext


async def create_numeric_code(
    db: AsyncSession,
    user_id: uuid.UUID,
    purpose: str,
    ttl: timedelta,
    length: int = 6,
) -> str:
    """Create a short numeric code (e.g. '194538') for manual entry.

    Uses ``secrets.randbelow`` so codes are uniformly distributed. Shorter
    codes are trivially brute-forceable over time — callers MUST enforce
    a short TTL (~15 min) and ideally rate-limit redemption attempts.
    """
    await invalidate_unused(db, user_id, purpose)

    upper = 10**length
    code = str(secrets.randbelow(upper)).zfill(length)
    token = AuthToken(
        user_id=user_id,
        token_hash=_hash(code),
        purpose=purpose,
        expires_at=_now() + ttl,
        created_at=_now(),
    )
    db.add(token)
    await db.flush()
    return code


async def redeem(
    db: AsyncSession,
    plaintext: str,
    purpose: str,
) -> uuid.UUID | None:
    """Validate + burn a token. Returns the owning user_id on success."""
    if not plaintext:
        return None

    result = await db.execute(
        select(AuthToken).where(
            AuthToken.token_hash == _hash(plaintext),
            AuthToken.purpose == purpose,
        )
    )
    token = result.scalar_one_or_none()
    if token is None:
        return None
    if token.used_at is not None:
        return None
    if token.expires_at < _now():
        return None

    token.used_at = _now()
    await db.flush()
    return token.user_id
