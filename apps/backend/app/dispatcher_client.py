"""Thin Python client for the dispatcher service.

All backend service-to-service calls (mail, socket, code-sandbox, other services)
should go through this client instead of hitting target hosts directly. Benefits:

- Single source of truth for target URLs (dispatcher's routes.json).
- Consistent auth (x-dispatcher-token).
- Consistent tracing headers (x-source-service = "backend").
- One place to add circuit breakers / metrics later.

We use the sync (`/dispatch/exchange`) pattern for everything — simpler single
code path. For fire-and-forget behaviour (email, notifications), wrap in
`sync_bg()` which schedules on the running loop and never raises into the caller.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx

from app.config import settings

logger = logging.getLogger("agentforge")

ServiceName = Literal["backend", "mail", "socket", "code-sandbox"]
HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]


class DispatcherClient:
    """HTTP client for dispatcher `/dispatch/exchange` endpoint."""

    def __init__(self, base_url: str, secret: str | None = None, source: str = "backend"):
        self._base_url = base_url.rstrip("/")
        self._secret = secret
        self._source = source

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "x-source-service": self._source,
        }
        if self._secret:
            headers["x-dispatcher-token"] = self._secret
        return headers

    async def sync(
        self,
        target: ServiceName,
        path: str,
        *,
        method: HttpMethod = "POST",
        body: Any = None,
        headers: dict[str, str] | None = None,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        """Synchronous proxy — waits for target response.

        Returns dispatcher envelope: ``{"status": int, "data": Any, "headers": {...}}``.
        Always returns (never raises HTTPError); check ``result["status"]`` for success.
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
        except Exception as exc:  # network error, timeout, JSON decode
            logger.exception("Dispatcher sync to %s %s crashed", target, path)
            return {"status": 500, "data": {"error": str(exc)}}

    def sync_bg(
        self,
        target: ServiceName,
        path: str,
        **kwargs: Any,
    ) -> None:
        """Fire-and-forget — schedule `sync()` on the running loop.

        Failures are logged but never raised. Use from request handlers so the
        HTTP response isn't blocked waiting for the downstream service.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning(
                "sync_bg(%s %s) called with no running event loop; skipping",
                target,
                path,
            )
            return

        loop.create_task(self._sync_and_log(target, path, **kwargs))

    async def _sync_and_log(self, target: str, path: str, **kwargs: Any) -> None:
        result = await self.sync(target, path, **kwargs)  # type: ignore[arg-type]
        status = result.get("status", 500)
        if status >= 400:
            logger.error(
                "Dispatcher → %s %s failed: status=%s data=%s",
                target,
                path,
                status,
                result.get("data"),
            )


# Module-level singleton configured from settings
dispatcher = DispatcherClient(
    base_url=settings.DISPATCHER_URL,
    secret=settings.DISPATCHER_SECRET or None,
)
