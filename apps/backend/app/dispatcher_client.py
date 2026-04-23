"""Python client for the dispatcher service.

Dispatcher exposes 4 patterns; this client wraps each with clear semantics:

    call()      → /dispatch/exchange  — sync HTTP proxy, waits for target response
    enqueue()   → /dispatch/internal  — publish to RabbitMQ, persistent + retry
    webhook()   → /dispatch/webhook   — external URL via queue, persistent + retry
    call_bg()   → /dispatch/exchange  — fire-and-forget wrapper around call()

Prefer `enqueue()` over `call_bg()` for any task you care about (e.g. emails,
ingestion). `call_bg` only gives fire-and-forget; `enqueue` gives durability,
retry, DLQ, and survives backend restart.

Benefits of routing everything through dispatcher:

- Single source of truth for target URLs (dispatcher's routes.json).
- Consistent auth (x-dispatcher-token).
- Consistent tracing (x-source-service).
- One place to add circuit breakers / metrics later.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal, TypedDict

import httpx

from app.config import settings

logger = logging.getLogger("agentforge")

ServiceName = Literal["backend", "mail", "socket", "code-sandbox"]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
Priority = Literal["low", "normal", "high"]


# ─── Response envelopes ────────────────────────────────────────────────


class ExchangeResponse(TypedDict, total=False):
    """Shape returned by `/dispatch/exchange`."""

    status: int
    data: Any
    headers: dict[str, str]


class EnqueueResponse(TypedDict):
    """Shape returned by `/dispatch/internal` and `/dispatch/webhook`."""

    success: bool
    messageId: str


class RetryConfig(TypedDict, total=False):
    maxAttempts: int
    backoffMs: int
    backoffMultiplier: int


# ─── Client ────────────────────────────────────────────────────────────


class DispatcherClient:
    """HTTP client for the dispatcher service (all 4 endpoints)."""

    def __init__(
        self,
        base_url: str,
        secret: str | None = None,
        source: str = "backend",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._secret = secret
        self._source = source

    # ── Sync proxy ────────────────────────────────────────────────────

    async def call(
        self,
        target: ServiceName,
        path: str,
        *,
        method: HttpMethod = "POST",
        body: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> ExchangeResponse:
        """Sync HTTP proxy — waits for target response.

        Returns ``{status, data, headers}``. Never raises; inspect ``status``
        (500 on network/decode errors).
        """
        payload = {
            "target": target,
            "path": path,
            "method": method,
            "body": body,
            "headers": headers,
            "timeout": int(timeout * 1000),
        }
        try:
            async with httpx.AsyncClient(timeout=timeout + 2) as client:
                resp = await client.post(
                    f"{self._base_url}/dispatch/exchange",
                    headers=self._headers(),
                    json=payload,
                )
                return resp.json()
        except Exception as exc:
            logger.exception("dispatcher call(%s %s) failed", target, path)
            return {"status": 500, "data": {"error": str(exc)}}

    def call_bg(
        self,
        target: ServiceName,
        path: str,
        **kwargs: Any,
    ) -> None:
        """Fire-and-forget wrapper around :meth:`call`.

        Schedules on the running loop. Failures are logged but never raised.
        Use only for transient operations (e.g. real-time socket emit) where
        retry/durability don't matter — otherwise prefer :meth:`enqueue`.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning(
                "call_bg(%s %s) called with no running loop; skipping", target, path
            )
            return
        loop.create_task(self._call_and_log(target, path, **kwargs))

    async def _call_and_log(self, target: ServiceName, path: str, **kwargs: Any) -> None:
        result = await self.call(target, path, **kwargs)
        if result.get("status", 500) >= 400:
            logger.error(
                "dispatcher call_bg → %s %s failed: status=%s data=%s",
                target, path, result.get("status"), result.get("data"),
            )

    # ── Async queue (durable + retry) ────────────────────────────────

    async def enqueue(
        self,
        target: ServiceName,
        path: str,
        *,
        event: str,
        body: Any = None,
        method: HttpMethod = "POST",
        headers: dict[str, str] | None = None,
        priority: Priority = "normal",
        retry: RetryConfig | None = None,
        correlation_id: str | None = None,
        timeout_ms: int = 30_000,
    ) -> EnqueueResponse:
        """Publish to RabbitMQ via `/dispatch/internal`. Persistent + retry.

        Dispatcher routes to a queue based on target + priority, then a consumer
        HTTP-calls the target. Failures are retried with exponential backoff;
        exhausted retries land in DLQ.

        ``event`` is a free-form tag used in logs (e.g. ``"document.ingest"``).
        """
        payload: dict[str, Any] = {
            "target": target,
            "path": path,
            "method": method,
            "body": body,
            "headers": headers,
            "timeout": timeout_ms,
            "source": self._source,
            "event": event,
            "priority": priority,
        }
        if retry is not None:
            payload["retry"] = retry
        if correlation_id is not None:
            payload["correlationId"] = correlation_id

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/dispatch/internal",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.exception(
                "dispatcher enqueue(%s %s event=%s) failed", target, path, event
            )
            return {"success": False, "messageId": ""}  # type: ignore[typeddict-item]

    async def webhook(
        self,
        url: str,
        *,
        event: str,
        body: Any = None,
        method: HttpMethod = "POST",
        headers: dict[str, str] | None = None,
        retry: RetryConfig | None = None,
        correlation_id: str | None = None,
        timeout_ms: int = 30_000,
    ) -> EnqueueResponse:
        """Send external webhook via `/dispatch/webhook`. Persistent + retry.

        Use for fire-and-forget calls to third-party endpoints. Same retry
        guarantees as :meth:`enqueue` but isolated on the ``webhook`` queue so
        a flaky partner can't starve internal traffic.
        """
        payload: dict[str, Any] = {
            "url": url,
            "method": method,
            "body": body,
            "headers": headers,
            "timeout": timeout_ms,
            "source": self._source,
            "event": event,
        }
        if retry is not None:
            payload["retry"] = retry
        if correlation_id is not None:
            payload["correlationId"] = correlation_id

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/dispatch/webhook",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            logger.exception(
                "dispatcher webhook(%s event=%s) failed", url, event
            )
            return {"success": False, "messageId": ""}  # type: ignore[typeddict-item]

    # ── Internals ────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "x-source-service": self._source,
        }
        if self._secret:
            headers["x-dispatcher-token"] = self._secret
        return headers


# Module-level singleton configured from settings
dispatcher = DispatcherClient(
    base_url=settings.DISPATCHER_URL,
    secret=settings.DISPATCHER_SECRET or None,
)
