"""Slack trigger CRUD + public Slack events receiver.

Two routers exported:
  router        — CRUD on /api/slack-triggers (cookie auth, workspace
                  scoped)
  events_router — public /api/slack/events (no auth; Slack signs
                  the request)
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.runtime.triggers.slack import service
from app.modules.runtime.triggers.slack.schemas import (
    SlackTriggerCreate,
    SlackTriggerResponse,
    SlackTriggerUpdate,
)
from app.modules.runtime.triggers.slack.signing import verify as verify_slack_signature
from app.platform.config import settings
from app.platform.db.session import async_session_factory, get_db

logger = logging.getLogger("agentforge")

router = APIRouter(prefix="/slack-triggers", tags=["slack-triggers"])
events_router = APIRouter(prefix="/slack", tags=["slack-events"])


# ─── CRUD ──────────────────────────────────────────────────────────


@router.get("", response_model=list[SlackTriggerResponse])
async def list_endpoint(
    workflow_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_triggers(db, workflow_id=workflow_id)
    return [SlackTriggerResponse.model_validate(r) for r in rows]


@router.post("", response_model=SlackTriggerResponse, status_code=201)
async def create_endpoint(
    payload: SlackTriggerCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await service.create_trigger(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return SlackTriggerResponse.model_validate(row)


@router.patch("/{trigger_id}", response_model=SlackTriggerResponse)
async def update_endpoint(
    trigger_id: uuid.UUID,
    payload: SlackTriggerUpdate,
    db: AsyncSession = Depends(get_db),
):
    row = await service.get_trigger(db, trigger_id)
    if row is None:
        raise HTTPException(status_code=404, detail="trigger_not_found")
    row = await service.update_trigger(db, row, payload)
    await db.commit()
    return SlackTriggerResponse.model_validate(row)


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


# ─── Public Slack events receiver ──────────────────────────────────


def _normalise_slash_command_payload(form: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Slack slash commands arrive as form-encoded. Lift them into
    the same shape as Events API messages for downstream dispatch.

    Returns (team_id, event_dict).
    """
    return form.get("team_id", ""), {
        "command": form.get("command"),
        "text": form.get("text"),
        "user_id": form.get("user_id"),
        "user_name": form.get("user_name"),
        "channel": form.get("channel_id"),
        "channel_name": form.get("channel_name"),
        "trigger_id": form.get("trigger_id"),
        "response_url": form.get("response_url"),
    }


@events_router.post("/events")
async def slack_events(request: Request):
    """Single endpoint for Events API + slash commands.

    Slack signing verification first, then branch on the payload
    shape. Returns immediately so Slack's 3s deadline isn't blown
    by the workflow execution (queued out-of-band).
    """
    if not settings.SLACK_SIGNING_SECRET:
        raise HTTPException(status_code=503, detail="slack_disabled")

    raw_body = await request.body()
    verify_slack_signature(
        raw_body=raw_body,
        signing_secret=settings.SLACK_SIGNING_SECRET,
        provided_signature=request.headers.get("x-slack-signature"),
        provided_timestamp=request.headers.get("x-slack-request-timestamp"),
        window_seconds=settings.SLACK_REPLAY_WINDOW_SECONDS,
    )

    # Slack sends JSON for Events API, form-urlencoded for slash
    # commands. Sniff the content-type.
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        body: dict[str, Any] = json.loads(raw_body or b"{}")
        # Slack URL verification handshake — first call after
        # adding the endpoint in the app config. Echo the challenge
        # so the dashboard marks it valid.
        if body.get("type") == "url_verification":
            return PlainTextResponse(content=body.get("challenge", ""))

        if body.get("type") == "event_callback":
            event = body.get("event") or {}
            event_type = event.get("type") or ""
            team_id = body.get("team_id") or event.get("team") or ""
            async with async_session_factory() as db:
                try:
                    await service.dispatch_event(
                        db,
                        team_id=team_id,
                        event_type=event_type,
                        event=event,
                    )
                    await db.commit()
                except Exception:
                    logger.exception("slack event dispatch failed")
                    await db.rollback()
                    # Still return 200 so Slack doesn't retry every
                    # event; the failure is logged + retryable via
                    # the FE "test now" handle.
            return JSONResponse({"ok": True})

        # Unknown JSON shape — acknowledge but don't dispatch.
        return JSONResponse({"ok": True, "skipped": True})

    # Form-encoded → slash command.
    form = await request.form()
    form_dict = {k: str(v) for k, v in form.items()}
    team_id, event = _normalise_slash_command_payload(form_dict)
    async with async_session_factory() as db:
        try:
            dispatched = await service.dispatch_event(
                db,
                team_id=team_id,
                event_type=service.SLACK_EVENT_SLASH_COMMAND,
                event=event,
            )
            await db.commit()
        except Exception:
            logger.exception("slack slash-command dispatch failed")
            await db.rollback()
            dispatched = 0

    # Slash commands expect a JSON response Slack renders to the
    # invoking user. Tiny ack here; richer responses can come from
    # the workflow's later POST to response_url.
    if dispatched > 0:
        return JSONResponse(
            {
                "response_type": "ephemeral",
                "text": "Working on it…",
            }
        )
    return JSONResponse(
        {
            "response_type": "ephemeral",
            "text": "No workflow is configured for this command.",
        }
    )
