"""Teams handler — :class:`WebhookTrigger` implementation."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from pydantic import BaseModel

from app.models.trigger import TRIGGER_TYPE_TEAMS, Trigger
from app.modules.runtime.triggers._base import WebhookTrigger
from app.modules.runtime.triggers._signing import verify_teams_hmac
from app.modules.runtime.triggers.schemas import TeamsConfig, TeamsCredentials
from app.platform.security.crypto import decrypt_secret


class TeamsHandler(WebhookTrigger):
    type = TRIGGER_TYPE_TEAMS
    label = "Microsoft Teams"
    config_schema = TeamsConfig
    credentials_schema = TeamsCredentials

    def secret_to_blob(self, credentials: BaseModel | None) -> str | None:
        """Teams stores just the b64 secret string — no JSON wrapping,
        for backwards-compat with the legacy ``hmac_secret_enc``
        column shape that the migration carried over."""
        if credentials is None:
            return None
        assert isinstance(credentials, TeamsCredentials)
        return credentials.hmac_secret_b64

    async def verify(self, request: Request, trigger: Trigger | None) -> None:
        """Teams URL routes are per-trigger (``/triggers/teams/{id}/events``)
        so the router resolved ``trigger`` before calling us."""
        if trigger is None:
            raise RuntimeError(
                "Teams verify() needs the trigger row resolved by the router."
            )
        body = await request.body()
        secret_b64 = (
            decrypt_secret(trigger.credentials_encrypted)
            if trigger.credentials_encrypted
            else None
        )
        verify_teams_hmac(
            raw_body=body,
            secret_b64=secret_b64,
            authorization_header=request.headers.get("authorization"),
        )

    async def parse(self, request: Request) -> dict[str, Any]:
        return await request.json()

    async def matches(self, trigger: Trigger, parsed: dict[str, Any]) -> bool:
        keyword = (trigger.config or {}).get("filter_keyword")
        if not keyword:
            return True
        text = parsed.get("text", "") if isinstance(parsed, dict) else ""
        return keyword.lower() in text.lower()


__all__ = ["TeamsHandler"]
