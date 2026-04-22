"""Service layer for AI credential CRUD with Fernet encryption."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_credentials.schemas import (
    AICredentialCreate,
    AICredentialResponse,
    AICredentialUpdate,
)
from app.config import settings
from app.models.ai_credential import AICredential


def _fernet() -> Fernet:
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
        raise ValueError("Failed to decrypt credential — invalid or corrupt ciphertext") from exc


def _mask(plaintext: str) -> str:
    if len(plaintext) <= 10:
        return "****"
    return plaintext[:6] + "•" * 8 + plaintext[-4:]


def _to_response(cred: AICredential, plaintext: str) -> AICredentialResponse:
    return AICredentialResponse(
        id=cred.id,
        provider=cred.provider,
        name=cred.name,
        last_used_at=cred.last_used_at,
        created_at=cred.created_at,
        masked_key=_mask(plaintext),
    )


# ── CRUD ──────────────────────────────────────────────────────────────

async def list_ai_credentials(
    db: AsyncSession, user_id: uuid.UUID
) -> list[AICredentialResponse]:
    result = await db.execute(
        select(AICredential)
        .where(AICredential.user_id == user_id)
        .order_by(AICredential.created_at.desc())
    )
    creds = result.scalars().all()
    return [_to_response(c, _decrypt(c.encrypted_key)) for c in creds]


async def get_ai_credential(
    db: AsyncSession, cred_id: uuid.UUID, user_id: uuid.UUID
) -> AICredentialResponse | None:
    result = await db.execute(
        select(AICredential).where(
            AICredential.id == cred_id, AICredential.user_id == user_id
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return None
    return _to_response(cred, _decrypt(cred.encrypted_key))


async def create_ai_credential(
    db: AsyncSession, user_id: uuid.UUID, data: AICredentialCreate
) -> AICredentialResponse:
    cred = AICredential(
        user_id=user_id,
        provider=data.provider,
        name=data.name,
        encrypted_key=_encrypt(data.plaintext_key),
    )
    db.add(cred)
    await db.flush()
    await db.refresh(cred)
    return _to_response(cred, data.plaintext_key)


async def update_ai_credential(
    db: AsyncSession,
    cred_id: uuid.UUID,
    user_id: uuid.UUID,
    data: AICredentialUpdate,
) -> AICredentialResponse | None:
    result = await db.execute(
        select(AICredential).where(
            AICredential.id == cred_id, AICredential.user_id == user_id
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return None

    if data.name is not None:
        cred.name = data.name

    await db.flush()
    return _to_response(cred, _decrypt(cred.encrypted_key))


async def delete_ai_credential(
    db: AsyncSession, cred_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    result = await db.execute(
        select(AICredential).where(
            AICredential.id == cred_id, AICredential.user_id == user_id
        )
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return False
    await db.delete(cred)
    return True


# ── Runtime lookup (used by executor) ────────────────────────────────

async def get_plaintext_key_by_id(
    db: AsyncSession, credential_id: uuid.UUID
) -> str | None:
    """Return the decrypted credential key by ID, or None."""
    result = await db.execute(
        select(AICredential).where(AICredential.id == credential_id)
    )
    cred = result.scalar_one_or_none()
    if not cred:
        return None

    plaintext = _decrypt(cred.encrypted_key)
    cred.last_used_at = datetime.now(timezone.utc)
    await db.flush()

    return plaintext
