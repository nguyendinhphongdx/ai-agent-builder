"""Langfuse ingestion via plain HTTP POST.

Avoids the ``langfuse`` Python SDK to keep the dep surface small —
the public ingestion API is documented + stable, and we only need
``trace-create`` + ``generation-create`` events. Falls back to a
log + swallow on any HTTP failure: LLM observability never blocks
the user's chat.

Reference:
  https://langfuse.com/docs/api#post-publicingestion

Each emit packs two events into one ingestion batch:
  1. ``trace-create``    creates the parent trace (one per LLM call).
  2. ``generation-create`` attaches model + tokens + cost + I/O.

We could batch across multiple calls, but the volume on a single
backend process makes per-call POSTs fine. Langfuse's collector
handles tens of millions of events; we're a rounding error.
"""
from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.platform.config import settings
from app.platform.observability.trace_provider.base import LLMTrace, TraceProvider

logger = logging.getLogger("agentforge")


class LangfuseProvider(TraceProvider):
    name = "langfuse"

    def __init__(self) -> None:
        self._base_url = (settings.LANGFUSE_HOST or "https://cloud.langfuse.com").rstrip("/")
        # Basic auth: ``public_key:secret_key`` base64-encoded. We
        # precompute once; key changes need a process restart.
        creds = f"{settings.LANGFUSE_PUBLIC_KEY}:{settings.LANGFUSE_SECRET_KEY}"
        self._auth = base64.b64encode(creds.encode()).decode()

    async def emit(self, trace: LLMTrace) -> None:
        if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
            return

        # Compose the two ingestion events. Langfuse's spec wants
        # ISO8601 timestamps in UTC; we mirror what we got from the
        # caller, defaulting both to now() so traces always have
        # bounds even for short-lived calls.
        started = (trace.started_at or datetime.now(timezone.utc)).isoformat()
        ended = (trace.ended_at or datetime.now(timezone.utc)).isoformat()
        generation_id = str(uuid.uuid4())

        events = [
            {
                "id": str(uuid.uuid4()),
                "type": "trace-create",
                "timestamp": started,
                "body": {
                    "id": trace.trace_id,
                    "name": trace.name,
                    "userId": str(trace.user_id) if trace.user_id else None,
                    "sessionId": str(trace.conversation_id) if trace.conversation_id else None,
                    "metadata": {
                        "workspace_id": str(trace.workspace_id) if trace.workspace_id else None,
                        "agent_id": str(trace.agent_id) if trace.agent_id else None,
                        **trace.metadata,
                    },
                },
            },
            {
                "id": str(uuid.uuid4()),
                "type": "generation-create",
                "timestamp": ended,
                "body": {
                    "id": generation_id,
                    "traceId": trace.trace_id,
                    "name": trace.name,
                    "model": trace.model_id,
                    "input": trace.messages,
                    "output": trace.output,
                    "startTime": started,
                    "endTime": ended,
                    "usage": {
                        "input": trace.prompt_tokens,
                        "output": trace.completion_tokens,
                        "total": trace.total_tokens,
                        "unit": "TOKENS",
                        "totalCost": trace.cost_usd,
                    },
                },
            },
        ]

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/api/public/ingestion",
                    headers={
                        "Authorization": f"Basic {self._auth}",
                        "Content-Type": "application/json",
                    },
                    json={"batch": events},
                )
            if resp.status_code >= 400:
                logger.warning(
                    "langfuse ingest: %d %s",
                    resp.status_code,
                    resp.text[:200],
                )
        except httpx.HTTPError as exc:
            logger.warning("langfuse ingest: %s", exc)
