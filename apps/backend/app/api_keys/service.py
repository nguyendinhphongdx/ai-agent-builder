"""Service layer for API key CRUD with Fernet encryption."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api_keys.schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyUpdate
from app.config import settings
from app.models.api_key import ApiKey


def _fernet() -> Fernet:
    """Return a Fernet instance using the configured encryption key."""
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"import secrets,base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())\""
        )
    return Fernet(settings.ENCRYPTION_KEY.encode())


def _encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Failed to decrypt API key — invalid or corrupt ciphertext") from exc


def _mask(plaintext: str) -> str:
    """Return a masked version: first 6 chars + *** + last 4 chars."""
    if len(plaintext) <= 10:
        return "****"
    return plaintext[:6] + "•" * 8 + plaintext[-4:]


def _to_response(key: ApiKey, plaintext: str) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=key.id,
        provider=key.provider,
        name=key.name,
        is_default=key.is_default,
        last_used_at=key.last_used_at,
        created_at=key.created_at,
        masked_key=_mask(plaintext),
    )


# ── CRUD ──────────────────────────────────────────────────────────────

async def list_api_keys(db: AsyncSession, user_id: uuid.UUID) -> list[ApiKeyResponse]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user_id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    return [_to_response(k, _decrypt(k.encrypted_key)) for k in keys]


async def get_api_key(
    db: AsyncSession, key_id: uuid.UUID, user_id: uuid.UUID
) -> ApiKeyResponse | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return None
    return _to_response(key, _decrypt(key.encrypted_key))


async def create_api_key(
    db: AsyncSession, user_id: uuid.UUID, data: ApiKeyCreate
) -> ApiKeyResponse:
    # If new key is default, clear existing defaults for this provider
    if data.is_default:
        await db.execute(
            update(ApiKey)
            .where(ApiKey.user_id == user_id, ApiKey.provider == data.provider)
            .values(is_default=False)
        )

    key = ApiKey(
        user_id=user_id,
        provider=data.provider,
        name=data.name,
        encrypted_key=_encrypt(data.plaintext_key),
        is_default=data.is_default,
    )
    db.add(key)
    await db.flush()
    await db.refresh(key)
    return _to_response(key, data.plaintext_key)


async def update_api_key(
    db: AsyncSession, key_id: uuid.UUID, user_id: uuid.UUID, data: ApiKeyUpdate
) -> ApiKeyResponse | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return None

    if data.name is not None:
        key.name = data.name

    if data.is_default is True:
        # Clear other defaults for the same provider
        await db.execute(
            update(ApiKey)
            .where(
                ApiKey.user_id == user_id,
                ApiKey.provider == key.provider,
                ApiKey.id != key_id,
            )
            .values(is_default=False)
        )
        key.is_default = True
    elif data.is_default is False:
        key.is_default = False

    await db.flush()
    return _to_response(key, _decrypt(key.encrypted_key))


async def delete_api_key(
    db: AsyncSession, key_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    await db.delete(key)
    return True


# ── Runtime lookup (used by executor) ────────────────────────────────

async def get_plaintext_key_for_provider(
    db: AsyncSession, user_id: uuid.UUID, provider: str
) -> str | None:
    """Return the decrypted default API key for a provider, or None."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.user_id == user_id,
            ApiKey.provider == provider,
            ApiKey.is_default == True,  # noqa: E712
        )
    )
    key = result.scalar_one_or_none()
    if not key:
        return None

    plaintext = _decrypt(key.encrypted_key)

    # Update last_used_at
    key.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    return plaintext
