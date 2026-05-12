"""Pydantic schemas for the unified trigger CRUD + per-type configs.

Each handler exposes a ``config_schema`` (and optional
``credentials_schema``) so the CRUD layer can validate user input
before persisting the JSONB. The router accepts a discriminated
union — ``type`` picks the right schema class.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.trigger import (
    TRIGGER_TYPE_DISCORD,
    TRIGGER_TYPE_EMAIL,
    TRIGGER_TYPE_SCHEDULED,
    TRIGGER_TYPE_SLACK,
    TRIGGER_TYPE_TEAMS,
)

# ─── Per-type config schemas ──────────────────────────────────────


class SlackConfig(BaseModel):
    """Slack event-stream filter. Signing secret is deployment-wide,
    not per-trigger — no credentials_schema needed."""

    slack_team_id: str = Field(min_length=1, max_length=64)
    filter_event_type: Literal["app_mention", "message", "slash_command"]
    filter_channel_id: str | None = None
    filter_command: str | None = None
    filter_keyword: str | None = None


class TeamsConfig(BaseModel):
    filter_keyword: str | None = None


class TeamsCredentials(BaseModel):
    """The base64 shared-secret Teams shows once at outgoing-webhook
    creation time. Stored as the literal base64 string (NOT a JSON
    wrapper) for backwards-compat with the legacy column."""

    hmac_secret_b64: str = Field(min_length=8)


class DiscordConfig(BaseModel):
    discord_application_id: str = Field(min_length=1, max_length=64)
    # Public key — NOT secret. Discord shows it in the dev portal.
    discord_public_key: str = Field(min_length=1, max_length=128)
    filter_command: str | None = None


class EmailConfig(BaseModel):
    imap_host: str
    imap_port: int = 993
    imap_use_ssl: bool = True
    imap_username: str
    imap_folder: str = "INBOX"
    poll_interval_seconds: int = Field(default=300, ge=30, le=86400)
    mark_seen: bool = True


class EmailCredentials(BaseModel):
    imap_password: str = Field(min_length=1)


class ScheduledConfig(BaseModel):
    node_id: uuid.UUID
    cron_expression: str = Field(min_length=1, max_length=128)
    timezone: str = Field(default="UTC", max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)


# ─── Generic CRUD shapes ──────────────────────────────────────────


class TriggerCreate(BaseModel):
    """One create payload for every type. ``type`` picks which
    ``config`` shape is valid — the service layer dispatches to the
    handler's ``config_schema`` for the real validation."""

    type: Literal[
        TRIGGER_TYPE_SLACK,
        TRIGGER_TYPE_TEAMS,
        TRIGGER_TYPE_DISCORD,
        TRIGGER_TYPE_EMAIL,
        TRIGGER_TYPE_SCHEDULED,
    ]
    workflow_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    config: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] | None = None
    is_active: bool = True


class TriggerUpdate(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    credentials: dict[str, Any] | None = None
    is_active: bool | None = None


class TriggerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    workflow_id: uuid.UUID
    name: str
    config: dict[str, Any]
    is_active: bool
    last_fired_at: datetime | None
    last_error: str | None
    next_run_at: datetime | None
    last_polled_at: datetime | None
    created_at: datetime
    updated_at: datetime


__all__ = [
    "SlackConfig",
    "TeamsConfig",
    "TeamsCredentials",
    "DiscordConfig",
    "EmailConfig",
    "EmailCredentials",
    "ScheduledConfig",
    "TriggerCreate",
    "TriggerUpdate",
    "TriggerResponse",
]
