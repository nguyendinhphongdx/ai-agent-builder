"""Unified trigger CRUD router.

  GET    /api/triggers                  list (workspace-scoped; ?type=, ?workflow_id=)
  POST   /api/triggers                  create (body picks type)
  GET    /api/triggers/{id}             read
  PATCH  /api/triggers/{id}             update
  DELETE /api/triggers/{id}             delete
  GET    /api/triggers/types            list known types + labels (for picker UI)

Per-type event receivers (Slack /events, Discord /interactions,
Teams /{id}/events, HTTP /workflow webhooks) live in their own
sub-routers under ``modules.runtime.triggers.<type>.router`` and are
wired separately in ``main.py`` — receivers have their own auth
shapes (signatures vs login cookies) so mounting them via this
router would muddy the dependency graph.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.auth.dependencies import get_current_user
from app.modules.runtime.triggers._registry import (
    TRIGGER_HANDLERS,
    UnknownTriggerType,
)
from app.modules.runtime.triggers.schemas import (
    TriggerCreate,
    TriggerResponse,
    TriggerUpdate,
)
from app.modules.runtime.triggers.service import (
    TriggerValidationError,
    create_trigger,
    delete_trigger,
    get_trigger,
    list_triggers,
    update_trigger,
)
from app.platform.db.session import get_db

router = APIRouter(
    prefix="/triggers",
    tags=["triggers"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/types")
async def list_known_types():
    """Picker UI fetches this on mount to render type cards."""
    return [
        {
            "type": h.type,
            "label": h.label,
            "needs_credentials": h.credentials_schema is not None,
        }
        for h in TRIGGER_HANDLERS.values()
    ]


@router.get("", response_model=list[TriggerResponse])
async def list_endpoint(
    type: str | None = Query(default=None),
    workflow_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_triggers(db, trigger_type=type, workflow_id=workflow_id)
    return [TriggerResponse.model_validate(r) for r in rows]


@router.post("", response_model=TriggerResponse, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    body: TriggerCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await create_trigger(
            db,
            trigger_type=body.type,
            workflow_id=body.workflow_id,
            name=body.name,
            config=body.config,
            credentials=body.credentials,
            is_active=body.is_active,
        )
    except TriggerValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except UnknownTriggerType as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    await db.commit()
    return TriggerResponse.model_validate(row)


@router.get("/{trigger_id}", response_model=TriggerResponse)
async def get_endpoint(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    row = await get_trigger(db, trigger_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trigger_not_found")
    return TriggerResponse.model_validate(row)


@router.patch("/{trigger_id}", response_model=TriggerResponse)
async def update_endpoint(
    trigger_id: uuid.UUID,
    body: TriggerUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await get_trigger(db, trigger_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trigger_not_found")
    try:
        row = await update_trigger(
            db,
            row,
            name=body.name,
            config=body.config,
            credentials=body.credentials,
            is_active=body.is_active,
        )
    except TriggerValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    await db.commit()
    return TriggerResponse.model_validate(row)


@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    row = await get_trigger(db, trigger_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trigger_not_found")
    await delete_trigger(db, row)
    await db.commit()
