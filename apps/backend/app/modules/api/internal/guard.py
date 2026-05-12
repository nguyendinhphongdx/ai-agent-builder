"""Guard for `/api/internal/*` endpoints — must be called from the dispatcher.

Dispatcher forwards `x-dispatcher-token` header on all server-to-server calls.
If `DISPATCHER_SECRET` is unset (dev), the guard is effectively disabled so
local curl still works; in prod set the secret to lock these routes down.
"""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.platform.config import settings


async def require_dispatcher(
    x_dispatcher_token: str | None = Header(default=None),
) -> None:
    """Dependency: reject requests that don't carry the dispatcher token.

    Mounted once on the `/internal` router so every sub-endpoint is protected.
    """
    expected = settings.DISPATCHER_SECRET
    if not expected:
        # Dev mode — no secret configured, allow through.
        return
    if x_dispatcher_token != expected:
        raise HTTPException(status_code=403, detail="Invalid dispatcher token")
