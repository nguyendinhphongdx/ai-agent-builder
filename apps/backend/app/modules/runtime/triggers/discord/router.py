"""Public Discord Interactions receiver.

Single endpoint: ``POST /api/triggers/discord/interactions``.

Discord delivers all interactions (slash commands + component
callbacks + autocomplete + PING) to one URL signed with Ed25519.
We resolve the trigger via the body's ``application_id`` *after*
the signature verifies, since Discord's public key is per-bot and
stored on the trigger row.

PING (type=1) verifies the endpoint and must echo back ``type=1``
immediately. Application commands (type=2) fan out into workflow
runs via the unified dispatcher.

CRUD lives in ``modules.runtime.triggers.router``.
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.models.trigger import TRIGGER_TYPE_DISCORD, Trigger
from app.modules.runtime.triggers._dispatch import enqueue_workflow_run
from app.modules.runtime.triggers._registry import get_handler
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

events_router = APIRouter(prefix="/triggers/discord", tags=["discord-events"])

_INTERACTION_PING = 1
_INTERACTION_APPLICATION_COMMAND = 2


@events_router.post("/interactions")
async def discord_interactions(request: Request):
    raw_body = await request.body()
    try:
        envelope = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="bad_json") from None

    application_id = str(envelope.get("application_id") or "")
    if not application_id:
        raise HTTPException(status_code=400, detail="missing_application_id")

    handler = get_handler(TRIGGER_TYPE_DISCORD)

    async with async_session_factory() as db:
        trigger = await db.scalar(
            select(Trigger).where(
                Trigger.type == TRIGGER_TYPE_DISCORD,
                Trigger.is_active.is_(True),
                Trigger.config["discord_application_id"].astext == application_id,
            )
        )
        if trigger is None:
            raise HTTPException(status_code=404, detail="trigger_not_found")

        await handler.verify(request, trigger)

        # Echo the PING handshake so Discord marks the endpoint valid.
        if envelope.get("type") == _INTERACTION_PING:
            return JSONResponse({"type": _INTERACTION_PING})

        if envelope.get("type") != _INTERACTION_APPLICATION_COMMAND:
            return JSONResponse({"type": 5})  # deferred — non-command

        if not await handler.matches(trigger, envelope):
            # Filter mismatch — ack-only, no workflow fired.
            return JSONResponse({"type": 5})

        try:
            await enqueue_workflow_run(db, trigger, source_payload=envelope)
            await db.commit()
        except Exception:
            logger.exception("discord interaction dispatch failed")
            await db.rollback()
            raise

    # Type 5 = DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE — Discord shows
    # "App is thinking…" and the workflow follows up via webhook.
    return JSONResponse({"type": 5})
