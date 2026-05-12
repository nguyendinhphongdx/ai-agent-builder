"""Abstract base classes for trigger types.

Two shapes, picked by how the external system delivers events:

  WebhookTrigger  HTTP-driven. Provider hits a route we expose with a
                  signed payload. We verify, parse, dispatch.
                  Implementations: slack, teams, discord, http.

  PollingTrigger  Pull-driven. A background loop ticks every N seconds,
                  checks an external source for events newer than the
                  last cursor, dispatches each.
                  Implementations: scheduled (cron), email (IMAP).

The base classes document the contract; today's concrete triggers
don't yet inherit (incremental adoption — each can flip when the next
change touches it). Use them as the template when adding the 7th
trigger.

Shared error class + signing helpers live in ``_signing.py``; common
dispatch (enqueue a workflow run job) is small enough that each
service-layer module duplicates it for now — extract here once a
third reuser shows up.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


class WebhookTrigger(ABC):
    """One subclass per HTTP-driven trigger type."""

    #: Stable id string used in router prefixes, logs, model rows.
    id: ClassVar[str]

    @abstractmethod
    async def verify(self, request: Request, trigger_row: Any) -> None:
        """Validate signatures + replay window. Raise
        ``TriggerAuthError`` (from _signing.py) on any failure. Must
        NOT consume the request body — read raw bytes via
        ``await request.body()``.
        """

    @abstractmethod
    async def parse(self, request: Request) -> dict[str, Any]:
        """Read the request body + headers and return a normalised
        dict that will land on the workflow run as ``input_data``.
        Provider-specific shape — callers downstream see the parsed
        payload, not raw HTTP."""

    @abstractmethod
    async def dispatch(
        self,
        db: AsyncSession,
        trigger_row: Any,
        payload: dict[str, Any],
    ) -> bool:
        """Apply per-trigger filters (keyword match, channel allow-list,
        etc.), enqueue a workflow run, return True iff dispatched."""


class PollingTrigger(ABC):
    """One subclass per pull-driven trigger type."""

    id: ClassVar[str]

    @abstractmethod
    async def tick(self, db: AsyncSession, trigger_row: Any) -> int:
        """Run one poll pass against the external source.

        Implementation responsibilities:
          1. Read ``trigger_row.cursor`` (or equivalent) to know
             where we left off.
          2. Fetch events newer than the cursor.
          3. For each event, dispatch a workflow run (mirror the
             Webhook ``dispatch`` shape).
          4. Persist the advanced cursor before returning.

        Returns the number of runs dispatched this tick (0 if nothing
        was due). Errors should be logged + reflected in
        ``trigger_row.last_error``, not raised — partial progress
        survives.
        """


__all__ = ["WebhookTrigger", "PollingTrigger"]
