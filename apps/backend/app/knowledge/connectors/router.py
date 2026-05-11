"""KB connector CRUD + manual-sync trigger.

Scheduled sync (every hour fire active connectors) lives in
``app.knowledge.connectors.scheduler`` and runs from the FastAPI
lifespan. This router exposes:

  /api/knowledge-bases/{kb_id}/connectors          GET / POST
  /api/knowledge-bases/{kb_id}/connectors/{id}     GET / PATCH / DELETE
  /api/knowledge-bases/{kb_id}/connectors/{id}/sync POST — fire now
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.knowledge.connectors.sync import run_connector
from app.knowledge.service import get_knowledge_base
from app.models.kb_connector import KBConnector as KBConnectorRow
from app.models.user import User
from app.permissions import catalogue as P
from app.security.crypto import encrypt_secret
from app.workspaces.permissions import require_active_permission

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/knowledge-bases", tags=["kb-connectors"])


# ─── Schemas ───────────────────────────────────────────────────────


class KBConnectorCreate(BaseModel):
    connector_type: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)
    # Plaintext credentials dict (e.g. {"access_key_id": "...",
    # "secret_access_key": "..."}). Encrypted server-side before
    # persisting; never echoed back.
    credentials: dict[str, Any] | None = None
    is_active: bool = True


class KBConnectorUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    is_active: bool | None = None


class KBConnectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    knowledge_base_id: uuid.UUID
    connector_type: str
    name: str
    config: dict[str, Any]
    is_active: bool
    last_sync_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class KBConnectorSyncResponse(BaseModel):
    discovered: int
    fetched: int
    failed: int
    errors: list[str]


def _to_response(row: KBConnectorRow) -> KBConnectorResponse:
    return KBConnectorResponse(
        id=row.id,
        knowledge_base_id=row.knowledge_base_id,
        connector_type=row.connector_type,
        name=row.name,
        config=row.config or {},
        is_active=row.is_active,
        last_sync_at=row.last_sync_at,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ─── List + create ─────────────────────────────────────────────────


@router.get(
    "/{kb_id}/connectors",
    response_model=list[KBConnectorResponse],
)
async def list_connectors(
    kb_id: uuid.UUID,
    _: Any = Depends(require_active_permission(P.KB_READ)),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    rows = (
        await db.scalars(
            select(KBConnectorRow)
            .where(KBConnectorRow.knowledge_base_id == kb_id)
            .order_by(KBConnectorRow.created_at)
        )
    ).all()
    return [_to_response(r) for r in rows]


@router.post(
    "/{kb_id}/connectors",
    response_model=KBConnectorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_connector(
    kb_id: uuid.UUID,
    body: KBConnectorCreate,
    current_user: User = Depends(get_current_user),
    _: Any = Depends(require_active_permission(P.KB_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    kb = await get_knowledge_base(db, kb_id)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    encrypted = (
        encrypt_secret(json.dumps(body.credentials))
        if body.credentials
        else None
    )
    row = KBConnectorRow(
        knowledge_base_id=kb_id,
        connector_type=body.connector_type,
        name=body.name,
        config=body.config,
        credentials_encrypted=encrypted,
        is_active=body.is_active,
        created_by=current_user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _to_response(row)


# ─── Single connector ──────────────────────────────────────────────


async def _get_or_404(
    db: AsyncSession, kb_id: uuid.UUID, connector_id: uuid.UUID
) -> KBConnectorRow:
    row = await db.scalar(
        select(KBConnectorRow).where(
            KBConnectorRow.id == connector_id,
            KBConnectorRow.knowledge_base_id == kb_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return row


@router.get(
    "/{kb_id}/connectors/{connector_id}",
    response_model=KBConnectorResponse,
)
async def get_connector(
    kb_id: uuid.UUID,
    connector_id: uuid.UUID,
    _: Any = Depends(require_active_permission(P.KB_READ)),
    db: AsyncSession = Depends(get_db),
):
    return _to_response(await _get_or_404(db, kb_id, connector_id))


@router.patch(
    "/{kb_id}/connectors/{connector_id}",
    response_model=KBConnectorResponse,
)
async def update_connector(
    kb_id: uuid.UUID,
    connector_id: uuid.UUID,
    body: KBConnectorUpdate,
    _: Any = Depends(require_active_permission(P.KB_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_404(db, kb_id, connector_id)
    if body.name is not None:
        row.name = body.name
    if body.config is not None:
        row.config = body.config
    if body.credentials is not None:
        # Empty dict deliberately clears the stored credentials — use
        # case is "rotate to ambient role" without leaving stale keys.
        row.credentials_encrypted = (
            encrypt_secret(json.dumps(body.credentials)) if body.credentials else None
        )
    if body.is_active is not None:
        row.is_active = body.is_active
    await db.commit()
    await db.refresh(row)
    return _to_response(row)


@router.delete(
    "/{kb_id}/connectors/{connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_connector(
    kb_id: uuid.UUID,
    connector_id: uuid.UUID,
    _: Any = Depends(require_active_permission(P.KB_UPDATE)),
    db: AsyncSession = Depends(get_db),
):
    row = await _get_or_404(db, kb_id, connector_id)
    await db.delete(row)
    await db.commit()


# ─── Manual sync ───────────────────────────────────────────────────


@router.post(
    "/{kb_id}/connectors/{connector_id}/sync",
    response_model=KBConnectorSyncResponse,
)
async def sync_connector(
    kb_id: uuid.UUID,
    connector_id: uuid.UUID,
    _: Any = Depends(require_active_permission(P.KB_DOCUMENT_UPLOAD)),
    db: AsyncSession = Depends(get_db),
):
    """Fire a one-off sync pass. For dev / immediate refresh — the
    scheduled tick handles periodic runs once that lands."""
    row = await _get_or_404(db, kb_id, connector_id)
    if not row.is_active:
        raise HTTPException(
            status_code=400,
            detail="Connector is inactive; flip is_active=true to enable.",
        )
    result = await run_connector(db, row)
    await db.commit()
    return KBConnectorSyncResponse(
        discovered=result.discovered,
        fetched=result.fetched,
        failed=result.failed,
        errors=result.errors,
    )
