"""Slack handler — Strategy implementation of :class:`WebhookTrigger`."""
from __future__ import annotations

from typing import Any

from fastapi import Request

from app.models.trigger import TRIGGER_TYPE_SLACK, Trigger
from app.modules.runtime.triggers._base import WebhookTrigger
from app.modules.runtime.triggers._signing import (
    TriggerAuthError,
    verify_slack_v0,
)
from app.modules.runtime.triggers.schemas import SlackConfig
from app.platform.config import settings

# Slack docs recommend 5min replay window.
_REPLAY_WINDOW_SECONDS = 300


class SlackHandler(WebhookTrigger):
    type = TRIGGER_TYPE_SLACK
    label = "Slack"
    config_schema = SlackConfig
    # Slack uses a deployment-wide ``SLACK_SIGNING_SECRET``; no per-
    # trigger secret.
    credentials_schema = None

    async def verify(self, request: Request, trigger: Trigger | None) -> None:
        """Verify the request was signed by the configured Slack app.
        ``trigger`` is None — Slack events arrive with the team id in
        the body; we verify the deployment signature first, then look
        up matching triggers in ``parse``/``matches``."""
        body = await request.body()
        verify_slack_v0(
            raw_body=body,
            signing_secret=getattr(settings, "SLACK_SIGNING_SECRET", None),
            signature_header=request.headers.get("x-slack-signature"),
            timestamp_header=request.headers.get("x-slack-request-timestamp"),
            window_seconds=_REPLAY_WINDOW_SECONDS,
        )

    async def parse(self, request: Request) -> dict[str, Any]:
        """Slack events come in two shapes:
          * JSON body for the Events API (event_callback envelope).
          * application/x-www-form-urlencoded for slash commands.
        ``parse`` only needs to return one normalised shape; the
        router decides which.
        """
        ctype = request.headers.get("content-type", "")
        if ctype.startswith("application/json"):
            data = await request.json()
            # Top-level envelope: type=event_callback, team_id, event{...}
            return {
                "envelope": data,
                "team_id": data.get("team_id"),
                "event_type": (data.get("event") or {}).get("type"),
                "event": data.get("event") or {},
            }
        # Slash command — form-urlencoded
        form = await request.form()
        return {
            "envelope": dict(form),
            "team_id": form.get("team_id"),
            "event_type": "slash_command",
            "event": dict(form),
        }

    async def matches(self, trigger: Trigger, parsed: dict[str, Any]) -> bool:
        cfg = trigger.config or {}
        if cfg.get("filter_event_type") != parsed.get("event_type"):
            return False
        event = parsed.get("event") or {}
        if cfg.get("filter_channel_id") and event.get("channel") != cfg.get(
            "filter_channel_id"
        ):
            return False
        if cfg.get("filter_command") and event.get("command") != cfg.get(
            "filter_command"
        ):
            return False
        keyword = cfg.get("filter_keyword")
        if keyword:
            text = event.get("text") or ""
            if keyword.lower() not in text.lower():
                return False
        return True


# Helper raised for symmetry with the import path callers expect.
__all__ = ["SlackHandler", "TriggerAuthError"]
