"""Service layer for AI credential CRUD with Fernet encryption."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_credential import AICredential
from app.modules.integrations.llm.credentials.schemas import (
    AICredentialCreate,
    AICredentialResponse,
    AICredentialUpdate,
)
from app.platform.context import current_user_id, current_workspace_id_or_none
from app.platform.security.crypto import decrypt_secret, encrypt_secret, mask_secret

# Module-local aliases keep the rest of the file's existing call sites
# (`_encrypt`, `_decrypt`, `_mask`) working without churn.
_encrypt = encrypt_secret
_decrypt = decrypt_secret
_mask = mask_secret


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

def _scope_filter(stmt):
    """Restrict to rows in the current workspace. No-op when no
    workspace is in context (background tasks)."""
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return stmt
    return stmt.where(AICredential.workspace_id == workspace_id)


async def list_ai_credentials(db: AsyncSession) -> list[AICredentialResponse]:
    stmt = (
        select(AICredential)
        .where(AICredential.user_id == current_user_id())
        .order_by(AICredential.created_at.desc())
    )
    result = await db.execute(_scope_filter(stmt))
    creds = result.scalars().all()
    return [_to_response(c, _decrypt(c.encrypted_key)) for c in creds]


async def get_ai_credential(
    db: AsyncSession, cred_id: uuid.UUID
) -> AICredentialResponse | None:
    stmt = select(AICredential).where(
        AICredential.id == cred_id,
        AICredential.user_id == current_user_id(),
    )
    result = await db.execute(_scope_filter(stmt))
    cred = result.scalar_one_or_none()
    if not cred:
        return None
    return _to_response(cred, _decrypt(cred.encrypted_key))


async def create_ai_credential(
    db: AsyncSession, data: AICredentialCreate
) -> AICredentialResponse:
    cred = AICredential(
        user_id=current_user_id(),
        # Auto-tag with the active workspace so list/get see it post-creation.
        workspace_id=current_workspace_id_or_none(),
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
    data: AICredentialUpdate,
) -> AICredentialResponse | None:
    stmt = select(AICredential).where(
        AICredential.id == cred_id,
        AICredential.user_id == current_user_id(),
    )
    result = await db.execute(_scope_filter(stmt))
    cred = result.scalar_one_or_none()
    if not cred:
        return None

    if data.name is not None:
        cred.name = data.name

    await db.flush()
    return _to_response(cred, _decrypt(cred.encrypted_key))


async def delete_ai_credential(db: AsyncSession, cred_id: uuid.UUID) -> bool:
    stmt = select(AICredential).where(
        AICredential.id == cred_id,
        AICredential.user_id == current_user_id(),
    )
    result = await db.execute(_scope_filter(stmt))
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
