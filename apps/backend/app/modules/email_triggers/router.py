"""CRUD endpoints for email triggers + a "test now" handle.

Multi-tenancy: the service layer reads ``current_workspace_id``
from the ContextVar so all queries are workspace-scoped without
the router having to thread it.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.email_triggers import service
from app.modules.email_triggers.schemas import (
    EmailTriggerCreate,
    EmailTriggerResponse,
    EmailTriggerUpdate,
)
from app.platform.db.session import get_db

router = APIRouter(prefix="/email-triggers", tags=["email-triggers"])


@router.get("", response_model=list[EmailTriggerResponse])
async def list_endpoint(
    workflow_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List triggers in the active workspace, optionally filtered to
    one workflow."""
    rows = await service.list_triggers(db, workflow_id=workflow_id)
    return [EmailTriggerResponse.model_validate(r) for r in rows]


@router.post("", response_model=EmailTriggerResponse, status_code=201)
async def create_endpoint(
    payload: EmailTriggerCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await service.create_trigger(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return EmailTriggerResponse.model_validate(row)


@router.patch("/{trigger_id}", response_model=EmailTriggerResponse)
async def update_endpoint(
    trigger_id: uuid.UUID,
    payload: EmailTriggerUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_trigger(db, trigger_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trigger_not_found")
    row = await service.update_trigger(db, row, payload)
    await db.commit()
    return EmailTriggerResponse.model_validate(row)


@router.delete("/{trigger_id}", status_code=204)
async def delete_endpoint(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_trigger(db, trigger_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trigger_not_found")
    await service.delete_trigger(db, row)
    await db.commit()
    return None


@router.post("/{trigger_id}/poll-now")
async def poll_now_endpoint(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Force one IMAP fetch right now — handy when debugging auth /
    folder names without waiting for the next sweep cadence.

    Honours the cursor: a backlog of 1000 old messages won't flood
    the workflow because the cursor is set on first poll.
    """
    row = await service.get_trigger(db, trigger_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trigger_not_found")
    dispatched = await service.poll_once(db, row)
    await db.commit()
    return {
        "dispatched": dispatched,
        "last_seen_uid": row.last_seen_uid,
        "last_error": row.last_error,
    }
