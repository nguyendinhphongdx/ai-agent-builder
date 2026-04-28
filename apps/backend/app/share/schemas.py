"""Schemas for the public share / embed-widget channel."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SharedAgentInfo(BaseModel):
    """Sanitised public view of an agent — what the embed widget needs to render.

    Deliberately omits anything sensitive: system prompt, model id, credential
    id, attached tools/KBs. Only branding + welcome message.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    avatar_url: str | None = None
    welcome_message: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    """Mirror of ``agent.share_settings`` — theme color, position, …"""


class ShareChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: uuid.UUID | None = None


class ShareChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    response: str
    latency_ms: int


class ShareSettingsUpdate(BaseModel):
    """Owner-side payload — toggle + customise share settings."""

    enabled: bool | None = None
    """Set False to revoke (clears share_token); True to enable (mints if missing)."""
    rotate: bool = False
    """When True, mint a fresh token even if one already exists."""
    settings: dict[str, Any] | None = None


class ShareConfigResponse(BaseModel):
    """Owner-side response — current share state for the agent editor UI."""

    enabled: bool
    share_token: str | None
    settings: dict[str, Any] = Field(default_factory=dict)
