"""Discord trigger CRUD + public Interactions receiver."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory, get_db
from app.discord_triggers import service
from app.models.discord_trigger import DiscordTrigger

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/discord-triggers", tags=["discord-triggers"])
events_router = APIRouter(prefix="/discord", tags=["discord-events"])


# ─── Schemas ─────────────────────────────────────────────────────


class DiscordTriggerCreate(BaseModel):
    workflow_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    discord_application_id: str = Field(min_length=1, max_length=64)
    discord_public_key: str = Field(min_length=64, max_length=128)
    filter_command: str | None = Field(default=None, max_length=64)
    is_active: bool = True


class DiscordTriggerResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    discord_application_id: str
    discord_public_key: str
    filter_command: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── CRUD ─────────────────────────────────────────────────────────


@router.get("", response_model=list[DiscordTriggerResponse])
async def list_endpoint(
    workflow_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_triggers(db, workflow_id=workflow_id)
    return [DiscordTriggerResponse.model_validate(r) for r in rows]


@router.post("", response_model=DiscordTriggerResponse, status_code=201)
async def create_endpoint(
    payload: DiscordTriggerCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await service.create_trigger(
            db,
            workflow_id=payload.workflow_id,
            name=payload.name,
            discord_application_id=payload.discord_application_id,
            discord_public_key=payload.discord_public_key,
            filter_command=payload.filter_command,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return DiscordTriggerResponse.model_validate(row)


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


# ─── Public Discord Interactions receiver ─────────────────────────


@events_router.post("/interactions")
async def discord_interactions(request: Request):
    """Single Interactions endpoint. Routes by application_id in the
    payload, verifies Ed25519 against the matching trigger's
    public_key, then dispatches matching workflows.

    Discord interaction types:
      1 = PING            reply with type=1 (PONG)
      2 = APPLICATION_COMMAND  → workflow dispatch
      others: ack only
    """
    raw_body = await request.body()
    try:
        payload: dict[str, Any] = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="bad_json") from None

    application_id = payload.get("application_id") or ""
    if not application_id:
        raise HTTPException(status_code=400, detail="missing_application_id")

    sig = request.headers.get("x-signature-ed25519")
    ts = request.headers.get("x-signature-timestamp")

    async with async_session_factory() as db:
        # Need the trigger row to know which public key to verify
        # against. Multiple triggers per app id can exist (different
        # workflows on the same bot) — verifying with the first
        # active one is fine because all triggers for the same app
        # share the same public key.
        row = await db.scalar(
            select(DiscordTrigger).where(
                DiscordTrigger.discord_application_id == application_id,
                DiscordTrigger.is_active.is_(True),
            )
        )
        if row is None:
            # No trigger configured → 401 not 404 so Discord retries
            # don't keep firing once we 200 above.
            raise HTTPException(status_code=401, detail="no_trigger_for_app")
        service.verify_signature(
            public_key_hex=row.discord_public_key,
            raw_body=raw_body,
            signature_hex=sig,
            timestamp=ts,
        )

        itype = payload.get("type")
        if itype == 1:
            return JSONResponse({"type": 1})

        if itype == 2:  # APPLICATION_COMMAND
            try:
                await service.dispatch_interaction(
                    db,
                    application_id=application_id,
                    interaction=payload,
                )
                await db.commit()
            except Exception:  # noqa: BLE001
                logger.exception("discord dispatch failed")
                await db.rollback()
            # Discord requires a response within 3s. type=5 is
            # "deferred" — the bot will follow up later via the
            # interaction-token URL (out of scope for v1).
            return JSONResponse({"type": 5})

        return JSONResponse({"type": 4, "data": {"content": "Unsupported interaction"}})
