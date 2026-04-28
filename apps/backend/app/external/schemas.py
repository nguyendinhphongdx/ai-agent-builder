"""Schemas for the public external API.

These are the **canonical, semver-stable** request/response shapes for 3rd-party
clients. Internal endpoints use richer types — keep these focused on what's
needed externally.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


# ─── Agents ─────────────────────────────────────────────────────────


class AgentSummary(BaseModel):
    """Public agent shape — omits internal fields like credential_id."""

    id: uuid.UUID
    name: str
    description: str | None
    model_id: str
    welcome_message: str | None
    status: str
    is_published: bool
    created_at: datetime
    updated_at: datetime


# ─── Chat ───────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Single chat turn payload.

    ``conversation_id`` is optional:
      - omitted → server creates a new conversation, returns its id in response
      - set     → continues an existing conversation owned by the same user
    """

    message: str
    conversation_id: uuid.UUID | None = None


class ChatResponse(BaseModel):
    """Sync chat response (non-streaming endpoint)."""

    conversation_id: uuid.UUID
    message_id: uuid.UUID
    response: str
    tokens_used: int | None = None
    latency_ms: int | None = None


# ─── Conversations ─────────────────────────────────────────────────


class ConversationSummary(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    title: str | None
    total_messages: int
    total_tokens: int
    last_message_at: datetime | None
    created_at: datetime


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    token_usage: dict | None
    latency_ms: int | None
    created_at: datetime
