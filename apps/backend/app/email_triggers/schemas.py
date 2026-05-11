"""Pydantic schemas for the email-trigger API.

Passwords are write-only — never returned in any response. The FE
shows "•••" placeholder and a "reset" button that prompts for a
fresh password on update.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EmailTriggerCreate(BaseModel):
    workflow_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    imap_host: str = Field(min_length=1, max_length=255)
    imap_port: int = Field(default=993, ge=1, le=65535)
    imap_use_ssl: bool = True
    imap_username: str = Field(min_length=1, max_length=255)
    imap_password: str = Field(min_length=1)
    imap_folder: str = Field(default="INBOX", max_length=255)
    poll_interval_seconds: int = Field(default=300, ge=60, le=3600)
    mark_seen: bool = True
    is_active: bool = True


class EmailTriggerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    imap_host: str | None = Field(default=None, max_length=255)
    imap_port: int | None = Field(default=None, ge=1, le=65535)
    imap_use_ssl: bool | None = None
    imap_username: str | None = Field(default=None, max_length=255)
    # Empty → unchanged. Senders pass a string only when rotating.
    imap_password: str | None = None
    imap_folder: str | None = Field(default=None, max_length=255)
    poll_interval_seconds: int | None = Field(default=None, ge=60, le=3600)
    mark_seen: bool | None = None
    is_active: bool | None = None


class EmailTriggerResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    imap_host: str
    imap_port: int
    imap_use_ssl: bool
    imap_username: str
    imap_folder: str
    poll_interval_seconds: int
    mark_seen: bool
    is_active: bool
    last_seen_uid: int | None
    last_polled_at: datetime | None
    last_error: str | None
    last_error_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
