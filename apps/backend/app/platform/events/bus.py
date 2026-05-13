"""Async in-process event bus.

One bus per process — exported as the module-level ``bus`` singleton.
Tests can construct their own ``EventBus()`` instance for isolation.

Semantics:

* ``emit(event)`` awaits every registered listener in the order they
  were subscribed. Listeners run sequentially so audit / notification
  ordering is deterministic.
* A listener raising never propagates: the bus logs the exception
  (with ``event_id`` + listener qualified name) and moves to the next.
  Listeners that must signal failure should write to a durable store
  (DB / queue) and let an out-of-band reconciler retry — the emit path
  is not the right place to surface telemetry errors.
* Listeners are coroutines (``async def``). Sync handlers aren't
  supported on purpose — most side effects (DB writes, HTTP calls)
  are async, and mixing sync/async invites accidental blocking.

The bus does *not* spawn tasks. If a caller wants fire-and-forget
emission outside the request scope, wrap the ``emit`` call with
``asyncio.create_task`` + ``run_in_request_context*`` from
``app.platform.context`` to keep ContextVars intact.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Awaitable, Callable, TypeVar

from app.platform.events.types import DomainEvent

logger = logging.getLogger("agentforge.events")

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[E], Awaitable[None]]


class EventBus:
    """Async in-process pub/sub over ``DomainEvent`` subclasses."""

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Handler[E]) -> None:
        """Register a listener for ``event_type``. Idempotent: registering
        the same callable twice would fire it twice — callers shouldn't
        do that, but the bus doesn't dedupe to keep semantics obvious."""
        self._handlers[event_type].append(handler)

    def on(self, event_type: type[E]) -> Callable[[Handler[E]], Handler[E]]:
        """Decorator sugar for :meth:`subscribe`.

        Usage::

            @bus.on(WorkspaceInvitationCreated)
            async def _audit(event: WorkspaceInvitationCreated) -> None:
                ...
        """

        def _decorator(handler: Handler[E]) -> Handler[E]:
            self.subscribe(event_type, handler)
            return handler

        return _decorator

    async def emit(self, event: DomainEvent) -> None:
        """Run every handler subscribed to ``type(event)``.

        Handlers are awaited sequentially. Exceptions are logged and
        swallowed so one bad listener doesn't break the rest — see
        module docstring for the rationale.
        """
        handlers = self._handlers.get(type(event))
        if not handlers:
            return
        for handler in handlers:
            try:
                await handler(event)
            except Exception:  # noqa: BLE001 — log + continue is the contract
                logger.exception(
                    "event handler %s.%s failed for %s(event_id=%s)",
                    handler.__module__,
                    getattr(handler, "__qualname__", repr(handler)),
                    type(event).__name__,
                    event.event_id,
                )

    def clear(self) -> None:
        """Drop every registered handler. Tests use this; production
        code should never need it."""
        self._handlers.clear()


# Process-wide singleton. Import this directly:
#   from app.platform.events import bus
bus = EventBus()
