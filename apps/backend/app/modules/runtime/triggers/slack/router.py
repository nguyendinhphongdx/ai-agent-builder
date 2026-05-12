"""Public Slack events receiver.

Single endpoint for Events API + slash commands. The Slack signing
secret is deployment-wide, so we verify *before* looking up which
trigger row (if any) matches the team_id in the body.

CRUD for Slack triggers now lives in the unified
``modules.runtime.triggers.router`` — this file only exports
``events_router`` (no auth dep; Slack signs the request).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import select

from app.models.trigger import TRIGGER_TYPE_SLACK, Trigger
from app.modules.runtime.triggers._dispatch import enqueue_workflow_run
from app.modules.runtime.triggers._registry import get_handler
from app.modules.runtime.triggers._signing import verify_slack_v0
from app.platform.config import settings
from app.platform.db.session import async_session_factory

logger = logging.getLogger("agentforge")

events_router = APIRouter(prefix="/slack", tags=["slack-events"])


def _normalise_slash_command(form: dict[str, Any]) -> dict[str, Any]:
    """Slack slash commands arrive form-encoded; lift to the same
    shape Events API messages use so downstream matching is one path."""
    return {
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
    """Receive Events API callbacks + slash commands.

    Returns 200 quickly (Slack's 3s deadline) — workflow dispatch
    runs synchronously here but the enqueue is fast; the workflow
    itself runs out-of-band on a worker."""
    if not settings.SLACK_SIGNING_SECRET:
        raise HTTPException(status_code=503, detail="slack_disabled")

    raw_body = await request.body()
    verify_slack_v0(
        raw_body=raw_body,
        signing_secret=settings.SLACK_SIGNING_SECRET,
        signature_header=request.headers.get("x-slack-signature"),
        timestamp_header=request.headers.get("x-slack-request-timestamp"),
        window_seconds=settings.SLACK_REPLAY_WINDOW_SECONDS,
    )

    content_type = request.headers.get("content-type", "")
    handler = get_handler(TRIGGER_TYPE_SLACK)

    if "application/json" in content_type:
        body: dict[str, Any] = json.loads(raw_body or b"{}")
        # URL verification handshake — Slack dashboard sends this once
        # to confirm we own the endpoint.
        if body.get("type") == "url_verification":
            return PlainTextResponse(content=body.get("challenge", ""))

        if body.get("type") == "event_callback":
            event = body.get("event") or {}
            team_id = body.get("team_id") or event.get("team") or ""
            parsed = {
                "envelope": body,
                "team_id": team_id,
                "event_type": event.get("type") or "",
                "event": event,
            }
            async with async_session_factory() as db:
                try:
                    await _dispatch_matching(db, handler, parsed)
                    await db.commit()
                except Exception:
                    logger.exception("slack event dispatch failed")
                    await db.rollback()
            return JSONResponse({"ok": True})

        return JSONResponse({"ok": True, "skipped": True})

    # Slash command — form-encoded.
    form = await request.form()
    form_dict = {k: str(v) for k, v in form.items()}
    parsed = {
        "envelope": form_dict,
        "team_id": form_dict.get("team_id", ""),
        "event_type": "slash_command",
        "event": _normalise_slash_command(form_dict),
    }

    dispatched = 0
    async with async_session_factory() as db:
        try:
            dispatched = await _dispatch_matching(db, handler, parsed)
            await db.commit()
        except Exception:
            logger.exception("slack slash-command dispatch failed")
            await db.rollback()

    if dispatched > 0:
        return JSONResponse(
            {"response_type": "ephemeral", "text": "Working on it…"}
        )
    return JSONResponse(
        {
            "response_type": "ephemeral",
            "text": "No workflow is configured for this command.",
        }
    )


async def _dispatch_matching(db, handler, parsed: dict[str, Any]) -> int:
    """Look up active Slack triggers for ``(team_id, event_type)``,
    apply the handler's matcher, enqueue runs for survivors. Returns
    dispatch count.

    Uses the partial expression index
    ``ix_triggers_slack_dispatch`` to keep this cheap on busy
    workspaces.
    """
    rows = (
        await db.execute(
            select(Trigger).where(
                Trigger.type == TRIGGER_TYPE_SLACK,
                Trigger.is_active.is_(True),
                Trigger.config["slack_team_id"].astext == parsed["team_id"],
                Trigger.config["filter_event_type"].astext == parsed["event_type"],
            )
        )
    ).scalars().all()

    dispatched = 0
    for trigger in rows:
        if not await handler.matches(trigger, parsed):
            continue
        ok = await enqueue_workflow_run(
            db, trigger, source_payload=parsed["envelope"]
        )
        if ok:
            dispatched += 1
    return dispatched
