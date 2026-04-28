"""Personal access token service — generate, hash, verify, scope checks."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.personal_access_token import PersonalAccessToken
from app.models.user import User
from app.personal_tokens.schemas import TokenCreate

# Plaintext token format: "afpt_<32 url-safe chars>".
TOKEN_PREFIX = "afpt_"
TOKEN_BODY_BYTES = 24  # 32 chars when base64-url encoded
PREFIX_DISPLAY_LEN = 12  # "afpt_a1b2c3" — enough to disambiguate in lists


# ─── Hash ───────────────────────────────────────────────────────────


def _hash(plaintext: str) -> str:
    """SHA-256 hex of the full plaintext token."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _generate_plaintext() -> str:
    """Cryptographically random token: ``afpt_<32 url-safe chars>``."""
    return TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_BODY_BYTES)


# ─── CRUD ───────────────────────────────────────────────────────────


async def list_tokens(
    db: AsyncSession, user_id: uuid.UUID
) -> list[PersonalAccessToken]:
    result = await db.execute(
        select(PersonalAccessToken)
        .where(PersonalAccessToken.user_id == user_id)
        .order_by(PersonalAccessToken.created_at.desc())
    )
    return list(result.scalars().all())


async def create_token(
    db: AsyncSession, user_id: uuid.UUID, data: TokenCreate
) -> tuple[PersonalAccessToken, str]:
    """Mint a new token for the user. Returns (row, plaintext) — caller MUST
    surface the plaintext to the user immediately and never store it."""
    plaintext = _generate_plaintext()
    token = PersonalAccessToken(
        user_id=user_id,
        name=data.name,
        key_hash=_hash(plaintext),
        key_prefix=plaintext[:PREFIX_DISPLAY_LEN],
        scopes=list(data.scopes),
        expires_at=data.expires_at,
    )
    db.add(token)
    await db.flush()
    await db.refresh(token)
    return token, plaintext


async def revoke_token(
    db: AsyncSession, token_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Soft-revoke. Row is kept for audit; ``revoked_at`` rejects future use."""
    result = await db.execute(
        select(PersonalAccessToken).where(
            PersonalAccessToken.id == token_id,
            PersonalAccessToken.user_id == user_id,
        )
    )
    token = result.scalar_one_or_none()
    if not token:
        return False
    token.revoked_at = datetime.now(timezone.utc)
    await db.flush()
    return True


# ─── Verification (called by auth dependency) ──────────────────────


async def verify_plaintext(
    db: AsyncSession, plaintext: str
) -> tuple[PersonalAccessToken, User] | None:
    """Resolve a raw token string to (token_row, owning_user) or None.

    Rejects: malformed prefix, unknown hash, revoked, expired. Refreshes
    ``last_used_at`` so the UI shows when each token was last seen.
    """
    if not plaintext.startswith(TOKEN_PREFIX):
        return None

    digest = _hash(plaintext)

    result = await db.execute(
        select(PersonalAccessToken).where(PersonalAccessToken.key_hash == digest)
    )
    token = result.scalar_one_or_none()
    if token is None:
        return None
    if token.revoked_at is not None:
        return None
    if token.expires_at is not None and token.expires_at <= datetime.now(timezone.utc):
        return None

    user_result = await db.execute(select(User).where(User.id == token.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None

    token.last_used_at = datetime.now(timezone.utc)
    # Don't await commit here — caller's session will commit at request end.
    await db.flush()

    return token, user
