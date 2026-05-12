"""Public Microsoft Teams events receiver.

Per-trigger URL: ``POST /api/triggers/teams/{trigger_id}/events``.
Teams Outgoing Webhook signs each request with the per-trigger HMAC
secret (stored Fernet-encrypted in the unified ``triggers`` row).

CRUD for Teams triggers lives in the unified
``modules.runtime.triggers.router``.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.models.trigger import TRIGGER_TYPE_TEAMS, Trigger
from app.modules.runtime.triggers._dispatch import enqueue_workflow_run
from app.modules.runtime.triggers._registry import get_handler
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

events_router = APIRouter(prefix="/triggers/teams", tags=["teams-events"])


@events_router.post("/{trigger_id}/events")
async def teams_events(trigger_id: uuid.UUID, request: Request):
    """Verify Teams HMAC, apply trigger filters, enqueue a run.
    Returns a small ack body — workflows write richer responses via
    Teams' response-url mechanism."""
    handler = get_handler(TRIGGER_TYPE_TEAMS)

    async with async_session_factory() as db:
        trigger = await db.scalar(
            select(Trigger).where(
                Trigger.id == trigger_id, Trigger.type == TRIGGER_TYPE_TEAMS
            )
        )
        if trigger is None or not trigger.is_active:
            raise HTTPException(status_code=404, detail="trigger_not_found")

        await handler.verify(request, trigger)
        payload = await handler.parse(request)
        if not await handler.matches(trigger, payload):
            return JSONResponse({"type": "message", "text": ""})

        try:
            await enqueue_workflow_run(db, trigger, source_payload=payload)
            await db.commit()
        except Exception:
            logger.exception("teams trigger %s dispatch failed", trigger_id)
            await db.rollback()
            raise

    return JSONResponse({"type": "message", "text": "Working on it…"})
