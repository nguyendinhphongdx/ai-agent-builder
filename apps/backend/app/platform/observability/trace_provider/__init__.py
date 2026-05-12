"""LLM trace-provider dispatch.

Distinct from app.platform.observability.tracing (which is OpenTelemetry +
generic distributed tracing). This module sends LLM-specific
events — full prompt/response payloads, token usage, scores — to
purpose-built platforms (Langfuse, LangSmith, Phoenix).

Why both:
  - OTEL gives you "the request hit /chat then queried Postgres
    then called the OpenAI HTTP endpoint" — the spans of a request.
  - An LLM trace platform gives you "agent X answered with this
    text given these messages and this system prompt; the user
    gave it a thumbs-down." That's the data product an ML team
    works against; OTEL doesn't have a native concept of "the
    rendered messages array".

Configuration is per-workspace (a future migration adds a
``workspace_settings.trace_provider`` column). For v1 the platform
single-tenant key in settings is enough — multi-workspace orgs
that need their own routing get a follow-up.
"""
from __future__ import annotations

import logging

from app.platform.config import settings
from app.platform.observability.trace_provider.base import (
    LLMTrace,
    TraceProvider,
)
from app.platform.observability.trace_provider.providers.langfuse import LangfuseProvider
from app.platform.observability.trace_provider.providers.noop import NoopProvider

logger = logging.getLogger("agentforge")

_provider: TraceProvider | None = None


def get_provider() -> TraceProvider:
    """Resolve the configured provider. Cached after the first call.

    Selection: explicit ``TRACE_PROVIDER`` setting > Langfuse if its
    keys are present > Noop (silent default — never raises, doesn't
    network).
    """
    global _provider
    if _provider is not None:
        return _provider

    explicit = (settings.TRACE_PROVIDER or "").lower().strip()
    if explicit == "langfuse" or (
        not explicit and settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY
    ):
        _provider = LangfuseProvider()
    else:
        _provider = NoopProvider()
    return _provider


__all__ = ["get_provider", "TraceProvider", "LLMTrace"]
