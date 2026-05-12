"""Discord handler — :class:`WebhookTrigger` implementation."""
from __future__ import annotations

from typing import Any

from fastapi import Request

from app.models.trigger import TRIGGER_TYPE_DISCORD, Trigger
from app.modules.runtime.triggers._base import WebhookTrigger
from app.modules.runtime.triggers._signing import verify_discord_ed25519
from app.modules.runtime.triggers.schemas import DiscordConfig

_REPLAY_WINDOW_SECONDS = 300


class DiscordHandler(WebhookTrigger):
    type = TRIGGER_TYPE_DISCORD
    label = "Discord"
    config_schema = DiscordConfig
    # Public key is in config (not secret), so no credentials_schema.
    credentials_schema = None

    async def verify(self, request: Request, trigger: Trigger | None) -> None:
        """Discord interactions are received at one shared route
        (``/triggers/discord/interactions``); the router resolves the
        trigger via ``application_id`` from the body BEFORE calling
        verify — at this point ``trigger`` is set."""
        if trigger is None:
            raise RuntimeError(
                "Discord verify() needs the trigger resolved by the router."
            )
        body = await request.body()
        cfg = trigger.config or {}
        verify_discord_ed25519(
            raw_body=body,
            public_key_hex=cfg.get("discord_public_key"),
            signature_hex=request.headers.get("x-signature-ed25519"),
            timestamp_header=request.headers.get("x-signature-timestamp"),
            window_seconds=_REPLAY_WINDOW_SECONDS,
        )

    async def parse(self, request: Request) -> dict[str, Any]:
        return await request.json()

    async def matches(self, trigger: Trigger, parsed: dict[str, Any]) -> bool:
        cfg = trigger.config or {}
        expected_cmd = cfg.get("filter_command")
        if not expected_cmd:
            return True
        data = parsed.get("data") or {}
        return data.get("name") == expected_cmd


__all__ = ["DiscordHandler"]
