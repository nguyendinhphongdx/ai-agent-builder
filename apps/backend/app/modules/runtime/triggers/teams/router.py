"""Teams trigger CRUD + public outgoing-webhook receiver."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.runtime.triggers.teams import service
from app.platform.db.session import async_session_factory, get_db

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/teams-triggers", tags=["teams-triggers"])
events_router = APIRouter(prefix="/teams", tags=["teams-events"])


# ─── Schemas (kept inline — small payload, only used here) ────────


class TeamsTriggerCreate(BaseModel):
    workflow_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    hmac_secret: str = Field(min_length=1)
    filter_keyword: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class TeamsTriggerResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    filter_keyword: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── CRUD ─────────────────────────────────────────────────────────


@router.get("", response_model=list[TeamsTriggerResponse])
async def list_endpoint(
    workflow_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_triggers(db, workflow_id=workflow_id)
    return [TeamsTriggerResponse.model_validate(r) for r in rows]


@router.post("", response_model=TeamsTriggerResponse, status_code=201)
async def create_endpoint(
    payload: TeamsTriggerCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await service.create_trigger(
            db,
            workflow_id=payload.workflow_id,
            name=payload.name,
            hmac_secret=payload.hmac_secret,
            filter_keyword=payload.filter_keyword,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return TeamsTriggerResponse.model_validate(row)


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


# ─── Public receiver ──────────────────────────────────────────────


@events_router.post("/events/{trigger_id}")
async def teams_events(trigger_id: uuid.UUID, request: Request):
    """Outgoing-webhook receiver. URL includes the trigger id so we
    know which secret to validate against without trusting the
    payload to identify itself.

    Response is rendered back in the Teams channel as a Bot card.
    """
    raw_body = await request.body()
    async with async_session_factory() as db:
        # No workspace ContextVar here — public endpoint, look up
        # globally. The secret check enforces tenant isolation.
        from sqlalchemy import select

        from app.models.teams_trigger import TeamsTrigger

        row = await db.scalar(
            select(TeamsTrigger).where(
                TeamsTrigger.id == trigger_id,
                TeamsTrigger.is_active.is_(True),
            )
        )
        if row is None:
            raise HTTPException(status_code=404, detail="trigger_not_found")

        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="bad_json") from None

        try:
            dispatched = await service.dispatch_event(
                db,
                row,
                raw_body=raw_body,
                auth_header=request.headers.get("authorization"),
                payload=payload,
            )
            await db.commit()
        except HTTPException:
            await db.rollback()
            raise
        except Exception:  # noqa: BLE001
            logger.exception("teams dispatch failed")
            await db.rollback()
            dispatched = False

    return JSONResponse(
        {
            "type": "message",
            "text": "Working on it…" if dispatched else "No workflow configured for this trigger.",
        }
    )
