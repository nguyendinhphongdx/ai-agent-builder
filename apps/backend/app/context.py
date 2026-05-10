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
# Active workspace for the request. Set by the auth dependency from
# ``user.default_workspace_id`` (or an ``X-Workspace-Id`` override
# header once that lands). Services that scope queries by tenant read
# this — see :func:`current_workspace_id`.
_current_workspace_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "current_workspace_id", default=None
)


def set_current_user_id(user_id: uuid.UUID) -> contextvars.Token[uuid.UUID | None]:
    """Set the current user for this request. Called by the auth dependency."""
    return _current_user_id.set(user_id)


def reset_current_user_id(token: contextvars.Token[uuid.UUID | None]) -> None:
    """Restore the previous value (paired with ``set_current_user_id``)."""
    _current_user_id.reset(token)


def set_current_workspace_id(
    workspace_id: uuid.UUID | None,
) -> contextvars.Token[uuid.UUID | None]:
    """Set the current workspace for this request. Pass ``None`` for
    cross-tenant or pre-multi-tenancy code paths."""
    return _current_workspace_id.set(workspace_id)


def reset_current_workspace_id(token: contextvars.Token[uuid.UUID | None]) -> None:
    """Restore the previous value (paired with ``set_current_workspace_id``)."""
    _current_workspace_id.reset(token)


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


def current_workspace_id_or_none() -> uuid.UUID | None:
    """Return the active workspace id, or ``None`` if the request is
    not workspace-scoped (background tasks, public webhooks, legacy
    rows still being backfilled).

    During the Phase 1.1 transition every service should read this
    rather than raise on missing — once backfill is complete and
    ``workspace_id`` columns flip to ``NOT NULL`` we can introduce a
    strict ``current_workspace_id()`` that raises like the user-id
    counterpart."""
    return _current_workspace_id.get()


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


def run_in_request_context_with_workspace(
    user_id: uuid.UUID, workspace_id: uuid.UUID | None, coro: Awaitable[T]
) -> Awaitable[T]:
    """Like :func:`run_in_request_context` but also propagates the
    workspace. Use for background jobs spawned from inside a tenant-
    scoped request (webhook delivery, async ingestion) so they keep
    seeing the same tenant in service queries."""

    async def _runner() -> T:
        u_token = set_current_user_id(user_id)
        w_token = set_current_workspace_id(workspace_id)
        try:
            return await coro
        finally:
            reset_current_workspace_id(w_token)
            reset_current_user_id(u_token)

    return _runner()
