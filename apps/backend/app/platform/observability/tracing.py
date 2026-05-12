"""OpenTelemetry bootstrap + helpers.

Tracing is OFF by default — every code path stays a no-op until the
operator sets ``OTEL_EXPORTER_OTLP_ENDPOINT``. That guarantee
matters: we don't want a deploy without a collector to log import
errors or burn CPU building spans no one consumes.

When enabled:
  - TracerProvider with the configured service name + OTLP gRPC
    exporter.
  - Auto-instrumentation for FastAPI (HTTP spans), SQLAlchemy (one
    span per query), Redis, and httpx (outbound HTTP including
    dispatcher + reranker + LLM API calls).
  - ``span(name, **attrs)`` helper for custom spans on the workflow
    runner + LLM executor.
"""
from __future__ import annotations

import contextlib
import logging
from typing import Any

from app.platform.config import settings

logger = logging.getLogger("agentforge")

_enabled = False
_tracer: Any = None


def is_enabled() -> bool:
    return _enabled


def init(app=None, *, engine=None) -> None:
    """Configure the SDK + auto-instrumentation.

    Idempotent: calling twice is a no-op. Pass ``app`` to enable
    FastAPI instrumentation and ``engine`` to instrument SQLAlchemy
    (the AsyncEngine's sync engine, since the SA instrumentation
    hooks on the underlying Engine).
    """
    global _enabled, _tracer

    endpoint = (settings.OTEL_EXPORTER_OTLP_ENDPOINT or "").strip()
    if not endpoint:
        # Off by default — no exporter, no instrumentation, no cost.
        return
    if _enabled:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning(
            "tracing: OTEL_EXPORTER_OTLP_ENDPOINT set but opentelemetry "
            "packages not installed — tracing remains off."
        )
        return

    resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)

    headers: dict[str, str] | None = None
    raw = (settings.OTEL_EXPORTER_OTLP_HEADERS or "").strip()
    if raw:
        # OTLP header spec: ``k1=v1,k2=v2``. Parse defensively.
        headers = {}
        for kv in raw.split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                headers[k.strip()] = v.strip()

    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=bool(settings.OTEL_EXPORTER_OTLP_INSECURE),
        headers=headers or None,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("agentforge")
    _enabled = True
    logger.info("tracing: OTLP exporter wired to %s", endpoint)

    # ── Auto-instrumentation ─────────────────────────────────────
    # Each import is guarded so missing optional packages don't
    # crash startup; users who install via `pip install -e ".[dev]"`
    # without the otel extra still boot.
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import (
                FastAPIInstrumentor,
            )

            FastAPIInstrumentor.instrument_app(app)
        except ImportError:
            logger.warning("tracing: opentelemetry-instrumentation-fastapi not installed")

    if engine is not None:
        try:
            from opentelemetry.instrumentation.sqlalchemy import (
                SQLAlchemyInstrumentor,
            )

            # Async engines expose .sync_engine — that's what SA
            # instrumentation hooks. Plain sync engines are themselves.
            target = getattr(engine, "sync_engine", engine)
            SQLAlchemyInstrumentor().instrument(engine=target)
        except ImportError:
            logger.warning("tracing: opentelemetry-instrumentation-sqlalchemy not installed")

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass


# ─── Custom-span helper ──────────────────────────────────────────


@contextlib.contextmanager
def span(name: str, **attrs: Any):
    """Open a span with ``name`` and the given attributes. No-op when
    tracing is disabled — callers can sprinkle this freely without
    worrying about overhead.

    Usage:
        with span("workflow.run", workflow_id=str(wf.id), node_count=42):
            ...
    """
    if not _enabled or _tracer is None:
        yield None
        return
    with _tracer.start_as_current_span(name) as s:
        for k, v in attrs.items():
            try:
                # Span attributes must be str/int/float/bool or a
                # sequence of one of those. Defensive str() catches
                # anything else (UUIDs, dicts, …).
                if isinstance(v, (str, int, float, bool)) or v is None:
                    if v is not None:
                        s.set_attribute(k, v)
                else:
                    s.set_attribute(k, str(v))
            except Exception:  # noqa: BLE001
                pass
        yield s


def record_exception(exc: BaseException) -> None:
    """Attach an exception event to the current span. No-op when
    tracing is off or there's no active span."""
    if not _enabled:
        return
    try:
        from opentelemetry import trace

        span_obj = trace.get_current_span()
        if span_obj.is_recording():
            span_obj.record_exception(exc)
            span_obj.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
    except Exception:  # noqa: BLE001
        pass


__all__ = ["init", "is_enabled", "span", "record_exception"]
