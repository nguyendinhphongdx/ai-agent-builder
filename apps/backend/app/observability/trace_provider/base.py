"""LLM trace-provider interface.

Single shape — ``LLMTrace`` — describing one LLM call with full
context (messages, model, usage). Each provider serialises into
its own native format.

The contract is intentionally fire-and-forget. Providers MUST NOT
raise — failures get logged + swallowed at the implementation layer.
LLM observability is nice-to-have, not on the critical path.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class LLMTrace:
    """One LLM call's worth of state, in a provider-neutral shape.

    Fields map to what every modern trace platform exposes — the
    provider-specific adapters fill in missing dimensions (e.g.
    Langfuse's "session id" → our conversation_id).
    """

    # Stable id for the call. UUID4 is fine; we don't need
    # cross-system continuity since each provider keeps its own ids.
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    # Free-form name to group related calls — "agent.chat",
    # "workflow.llm_node", etc.
    name: str = "llm.call"
    # provider/model = "openai/gpt-4o" (matches agent.model_id shape).
    model_id: str | None = None
    # Rendered LangChain-style messages array — the ground truth of
    # what the model actually saw.
    messages: list[dict[str, Any]] = field(default_factory=list)
    # Final assistant content (post-stream).
    output: str | None = None
    # Token counts, normalized across providers.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    # USD cost computed via app.usage.pricing.
    cost_usd: float | None = None
    # End-to-end latency from request start to final token.
    latency_ms: int | None = None
    # Tenant / business context — providers map these onto their
    # native session/user fields.
    workspace_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    conversation_id: uuid.UUID | None = None
    # Free-form metadata bag for anything not in the canonical set
    # (tool calls, attempt count, parent-trace id, …).
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    ended_at: datetime | None = None


class TraceProvider(ABC):
    """One subclass per platform. Stateless aside from internal
    HTTP-client caching."""

    name: str

    @abstractmethod
    async def emit(self, trace: LLMTrace) -> None:
        """Submit one trace. MUST NOT raise — log + swallow on failure."""

    async def flush(self) -> None:
        """Optional: drain any batched writes. Called on app shutdown
        from the lifespan hook. Default is a no-op."""
