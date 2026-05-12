"""Response shapes for the personal dashboard."""
from __future__ import annotations

from pydantic import BaseModel


class AgentsStats(BaseModel):
    total: int
    by_status: dict[str, int]
    """e.g. ``{"draft": 2, "published": 10}`` — empty buckets are omitted."""


class ConversationsStats(BaseModel):
    total: int
    last_30d: int


class MessagesStats(BaseModel):
    total: int
    last_30d: int


class TokensByModel(BaseModel):
    model: str
    """Free-form provider/model id from `messages.llm_model` (e.g. "openai/gpt-4o-mini")."""
    tokens: int


class TokensStats(BaseModel):
    total: int
    """Sum of `conversation.total_tokens` for the user — cheaper than aggregating
    per-message JSONB and matches the counter the chat runner already maintains."""
    by_model: list[TokensByModel]
    """Per-model breakdown computed from `messages.llm_model` + `messages.token_usage`."""


class CurrencyRevenue(BaseModel):
    """Revenue split per currency — we don't convert across currencies."""

    currency: str
    gross_cents: int
    fees_cents: int
    net_cents: int
    count: int


class RevenueSummary(BaseModel):
    by_currency: list[CurrencyRevenue]
    total_paid: int
    total_refunded: int


class DashboardResponse(BaseModel):
    """Combined dashboard payload — single round-trip from the homepage."""

    agents: AgentsStats
    conversations: ConversationsStats
    messages: MessagesStats
    tokens: TokensStats
    revenue: RevenueSummary
