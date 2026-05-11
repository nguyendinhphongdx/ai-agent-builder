"""Noop trace provider — the default when nothing is configured.

Used so callers can ``await get_provider().emit(...)`` without
checking whether observability is enabled. Costs one function
call and a coroutine allocation per LLM event, which is in the
noise next to the actual LLM latency.
"""
from __future__ import annotations

from app.observability.trace_provider.base import LLMTrace, TraceProvider


class NoopProvider(TraceProvider):
    name = "noop"

    async def emit(self, trace: LLMTrace) -> None:
        return None
