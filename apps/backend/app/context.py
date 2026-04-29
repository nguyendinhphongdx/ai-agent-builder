"""Request-scoped context vars (PEP 567).

Lets services read the authenticated user without threading ``user_id``
through every function call. Set once in ``get_current_user`` (the auth
dependency); read via :func:`current_user_id` anywhere downstream in the same
async task.

Why ContextVar and not ``request.state``:
- Works in service-layer code that doesn't see the FastAPI ``Request`` object.
- Async-safe: each request runs in its own task, contextvars are per-task.
- Plays nicely with ``asyncio.create_task`` *if* you copy the context
  (``contextvars.copy_context()``) — see :func:`run_in_request_context` for
  background tasks that need to inherit the user.

When NOT to use it:
- For **input parameters** to long-lived domain functions where being explicit
  matters for testing — keep ``user_id`` in the signature.
- For **batch jobs** with no inherent user — pass explicitly.
"""

from __future__ import annotations

import contextvars
import uuid
from typing import Awaitable, TypeVar

_current_user_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "current_user_id", default=None
)


def set_current_user_id(user_id: uuid.UUID) -> contextvars.Token[uuid.UUID | None]:
    """Set the current user for this request. Called by the auth dependency."""
    return _current_user_id.set(user_id)


def reset_current_user_id(token: contextvars.Token[uuid.UUID | None]) -> None:
    """Restore the previous value (paired with ``set_current_user_id``)."""
    _current_user_id.reset(token)


def current_user_id() -> uuid.UUID:
    """Return the authenticated user id; raise if no user is in scope.

    Use this in services that are *only* ever called from authenticated
    request handlers. If a service is also reachable from background tasks or
    public webhooks, prefer :func:`current_user_id_or_none` and handle ``None``
    explicitly.
    """
    user_id = _current_user_id.get()
    if user_id is None:
        raise RuntimeError(
            "current_user_id() called outside an authenticated request scope"
        )
    return user_id


def current_user_id_or_none() -> uuid.UUID | None:
    """Like :func:`current_user_id` but returns ``None`` instead of raising."""
    return _current_user_id.get()


T = TypeVar("T")


def run_in_request_context(
    user_id: uuid.UUID, coro: Awaitable[T]
) -> Awaitable[T]:
    """Wrap a coroutine so it sees ``user_id`` via contextvars.

    Use when spawning a background task (``asyncio.create_task(...)``) that
    needs to call services using :func:`current_user_id`. Returns the coroutine
    to await — the caller decides how to schedule it.
    """

    async def _runner() -> T:
        token = set_current_user_id(user_id)
        try:
            return await coro
        finally:
            reset_current_user_id(token)

    return _runner()
