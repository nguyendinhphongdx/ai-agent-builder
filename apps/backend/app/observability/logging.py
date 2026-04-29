"""Structured request logging.

Replaces the human-readable ``→ GET /path`` / ``← GET /path 200 (12ms)``
text logger with a single JSON line per request that downstream tooling
(Datadog, Loki, CloudWatch Logs Insights) can parse without regex:

    {"ts":"2026-04-29T14:00:00Z","level":"INFO","msg":"http_request",
     "method":"GET","path":"/api/agents","status":200,"latency_ms":12,
     "request_id":"01HW...","user_id":"a1b2..."}

Wires together:
- ``RequestIdMiddleware`` — assigns/echoes ``X-Request-ID`` (clients can
  pass one in to correlate); stores it in a ContextVar so deeper logs
  can include it without threading.
- ``StructuredLoggingMiddleware`` — emits the per-request JSON line.
- ``JsonFormatter`` — installed on the root logger so ad-hoc
  ``logger.warning(...)`` calls also come out as JSON in production.

Set ``LOG_FORMAT=json`` to enable; default is the existing text format.
"""
from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.context import current_user_id_or_none

logger = logging.getLogger("agentforge.access")

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id", default=None
)


def current_request_id() -> str | None:
    """Read the current request id (set by RequestIdMiddleware)."""
    return _request_id.get()


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line.

    Includes the standard fields plus ``request_id`` (from contextvar)
    when present. Custom keys passed via ``logger.info("...", extra={...})``
    flow through unchanged.
    """

    _RESERVED = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if (rid := _request_id.get()) is not None:
            out["request_id"] = rid
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                out[key] = value
        if record.exc_info:
            out["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign or echo ``X-Request-ID`` and stash it in the contextvar."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = _request_id.set(rid)
        try:
            response = await call_next(request)
        finally:
            _request_id.reset(token)
        response.headers["X-Request-ID"] = rid
        return response


class StructuredAccessLogMiddleware(BaseHTTPMiddleware):
    """Emit one JSON access-log line per request."""

    SILENT_PREFIXES = ("/uploads/", "/healthz", "/readyz")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(self.SILENT_PREFIXES):
            return await call_next(request)
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        user_id = current_user_id_or_none()
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "user_id": str(user_id) if user_id else None,
                "client": request.client.host if request.client else None,
            },
        )
        return response


def install_json_formatter() -> None:
    """Replace handler formatters on the root logger with the JSON one."""
    formatter = JsonFormatter()
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)
