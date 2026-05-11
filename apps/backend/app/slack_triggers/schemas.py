"""Pydantic schemas for the slack-trigger API."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SlackTriggerCreate(BaseModel):
    workflow_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    slack_team_id: str = Field(min_length=1, max_length=64)
    filter_event_type: str = Field(min_length=1, max_length=32)
    filter_channel_id: str | None = Field(default=None, max_length=64)
    filter_command: str | None = Field(default=None, max_length=64)
    filter_keyword: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class SlackTriggerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slack_team_id: str | None = Field(default=None, max_length=64)
    filter_event_type: str | None = Field(default=None, max_length=32)
    filter_channel_id: str | None = Field(default=None, max_length=64)
    filter_command: str | None = Field(default=None, max_length=64)
    filter_keyword: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class SlackTriggerResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slack_team_id: str
    filter_event_type: str
    filter_channel_id: str | None
    filter_command: str | None
    filter_keyword: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
