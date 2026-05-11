"""Prometheus metric registry + HTTP middleware + /metrics endpoint.

Every metric lives in ONE module so a quick read tells you what
the scraper sees. Adding a metric is two lines:
  1. Declare it next to its peers below.
  2. Increment/observe it at the call site.

Counters are monotonic; reset on process restart. Histograms use
bucket sets tuned to web-app latencies (sub-100ms common, with
tails out to 10s for LLM calls).
"""
from __future__ import annotations

import time
from typing import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware

# Use a dedicated registry rather than the default global. Two reasons:
#   1. Lets tests reset the registry without affecting other test modules.
#   2. Plays nicer with multi-process deployments — Gunicorn workers
#      can each ship their own registry without colliding on the
#      default's process-wide singletons.
REGISTRY = CollectorRegistry(auto_describe=True)


# ─── HTTP request metrics ─────────────────────────────────────────


_http_buckets = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0
)

http_requests_total = Counter(
    "agentforge_http_requests_total",
    "Count of HTTP requests by method, path template, and status class.",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)
http_request_duration_seconds = Histogram(
    "agentforge_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=("method", "path"),
    buckets=_http_buckets,
    registry=REGISTRY,
)


# ─── LLM / cost metrics ───────────────────────────────────────────


llm_tokens_total = Counter(
    "agentforge_llm_tokens_total",
    "Total LLM tokens consumed, labeled by provider/model/direction.",
    labelnames=("provider", "model", "direction"),
    registry=REGISTRY,
)
llm_cost_usd_total = Counter(
    "agentforge_llm_cost_usd_total",
    "Total LLM spend in USD.",
    labelnames=("provider", "model"),
    registry=REGISTRY,
)
llm_call_duration_seconds = Histogram(
    "agentforge_llm_call_duration_seconds",
    "Latency of a single LLM call from request to last token.",
    labelnames=("provider", "model"),
    # LLMs are slower than DB queries — bucket out to 60s.
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0),
    registry=REGISTRY,
)


# ─── Knowledge retrieval ──────────────────────────────────────────


kb_query_duration_seconds = Histogram(
    "agentforge_kb_query_duration_seconds",
    "Knowledge base retrieval latency (vector + hybrid + rerank).",
    labelnames=("mode",),  # "vector" | "hybrid" | "hybrid_rerank"
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=REGISTRY,
)


# ─── Job queue ────────────────────────────────────────────────────


job_processing_duration_seconds = Histogram(
    "agentforge_job_processing_duration_seconds",
    "Time from job dequeue to terminal state.",
    labelnames=("job_type", "status"),  # status ∈ {completed, failed, dead}
    buckets=(0.1, 0.5, 1.0, 5.0, 30.0, 120.0, 600.0),
    registry=REGISTRY,
)
job_queue_depth = Gauge(
    "agentforge_job_queue_depth",
    "Number of jobs currently in a non-terminal state.",
    labelnames=("status",),  # queued | running | failed
    registry=REGISTRY,
)


# ─── Workflow runs ────────────────────────────────────────────────


workflow_run_duration_seconds = Histogram(
    "agentforge_workflow_run_duration_seconds",
    "Workflow execution time end-to-end.",
    labelnames=("status",),
    buckets=(0.1, 0.5, 1.0, 5.0, 30.0, 120.0, 600.0),
    registry=REGISTRY,
)


# ─── HTTP middleware ──────────────────────────────────────────────


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Stamp request count + latency for every HTTP request.

    Path templating uses the matched route's path (``/agents/{id}``)
    rather than the raw URL so we don't explode cardinality with
    per-id labels. Unmatched routes fall back to "unknown".
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = _route_path(request)
        method = request.method
        if path == "/metrics":
            # Don't count the scraper itself — pollutes the signal.
            return await call_next(request)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            http_requests_total.labels(method=method, path=path, status="5xx").inc()
            raise

        elapsed = time.perf_counter() - start
        status_class = f"{response.status_code // 100}xx"
        http_requests_total.labels(method=method, path=path, status=status_class).inc()
        http_request_duration_seconds.labels(method=method, path=path).observe(elapsed)
        return response


def _route_path(request: Request) -> str:
    """Resolve the matched route template, or ``"unknown"``.

    FastAPI sets ``request.scope["route"]`` after matching. For 404s
    (no match), nothing is set and we report ``unknown``.
    """
    route = request.scope.get("route")
    if route is not None and getattr(route, "path", None):
        return route.path
    return "unknown"


# ─── /metrics endpoint installer ──────────────────────────────────


def install(app: FastAPI) -> None:
    """Mount the middleware + ``/metrics`` route. Call from
    ``create_app()`` after the rest of the middleware stack is set up
    (order matters: PrometheusMiddleware must wrap the route handler
    so it sees the matched route)."""
    app.add_middleware(PrometheusMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        # Plain text exposition format — Prometheus + every Prom-
        # compatible scraper (Grafana Cloud, VictoriaMetrics, …)
        # reads this directly.
        body = generate_latest(REGISTRY)
        return Response(content=body, media_type=CONTENT_TYPE_LATEST)


__all__ = [
    "REGISTRY",
    "install",
    "PrometheusMiddleware",
    "http_requests_total",
    "http_request_duration_seconds",
    "llm_tokens_total",
    "llm_cost_usd_total",
    "llm_call_duration_seconds",
    "kb_query_duration_seconds",
    "job_processing_duration_seconds",
    "job_queue_depth",
    "workflow_run_duration_seconds",
]
