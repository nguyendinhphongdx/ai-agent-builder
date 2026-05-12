"""Trigger handler abstraction — Strategy pattern.

Each trigger type has exactly one ``TriggerHandler`` subclass that
knows:
  * the JSONB shape its config column should contain
    (``config_schema`` — Pydantic; validated at create/update time)
  * whether it ever needs a Fernet-encrypted credentials blob
    (``credentials_schema``, optional)
  * how to receive events (webhook ``verify``/``parse`` or polling
    ``tick``)

The service layer calls handlers via ``app.modules.runtime.triggers
._registry.get_handler(type)`` — no per-type ``if/elif`` in the CRUD
or dispatch code. Adding a 6th provider = subclass + register, no
DB migration, no router touch.

Two intermediate ABCs (``WebhookTrigger`` and ``PollingTrigger``)
codify the two activation shapes so concrete handlers only fill in
the per-provider quirks. Mixing both is not supported — pick one.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from fastapi import Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger import Trigger


class TriggerHandler(ABC):
    """Common surface across all trigger types.

    The CRUD layer uses ``config_schema`` to validate user-supplied
    JSON before persisting. ``credentials_schema`` (optional) does
    the same for the encrypted blob.
    """

    #: Discriminator value. Must match the row's ``type`` column and
    #: the registry key. Use one of the ``TRIGGER_TYPE_*`` constants
    #: from ``app.models.trigger``.
    type: ClassVar[str]

    #: User-facing label for picker / settings UI.
    label: ClassVar[str]

    #: Pydantic schema for the ``config`` JSONB.
    config_schema: ClassVar[type[BaseModel]]

    #: Optional Pydantic schema for plaintext credentials (before
    #: Fernet encrypt). ``None`` when the provider has no per-trigger
    #: secret.
    credentials_schema: ClassVar[type[BaseModel] | None] = None

    def secret_to_blob(self, credentials: BaseModel | None) -> str | None:
        """Serialise plaintext credentials to a JSON string the
        service layer will Fernet-encrypt. Override for non-default
        shapes (Teams stores just the b64 secret, not a JSON dict).
        """
        if credentials is None:
            return None
        return credentials.model_dump_json()


class WebhookTrigger(TriggerHandler):
    """HTTP-driven trigger. Provider hits ``/api/triggers/<type>/events``
    (or a per-trigger URL for shapes that need it). We verify the
    signature, parse the payload into a normalised dict, then the
    service layer's ``dispatch`` enqueues a workflow run."""

    @abstractmethod
    async def verify(self, request: Request, trigger: Trigger | None) -> None:
        """Raise ``TriggerAuthError`` (from ``_signing.py``) on any
        signature / replay-window failure. ``trigger`` is None when
        the verifier needs to resolve the trigger row AFTER verifying
        the request envelope (Slack, Discord — verified by deployment
        secret first, trigger lookup later)."""

    @abstractmethod
    async def parse(self, request: Request) -> dict[str, Any]:
        """Read the request body + headers, return the normalised
        ``input_data`` shape downstream workflows will see. Provider-
        specific (Slack event vs Discord interaction vs raw POST)."""

    async def matches(
        self, trigger: Trigger, parsed: dict[str, Any]
    ) -> bool:
        """Apply per-trigger filters from ``trigger.config`` against
        the parsed payload. Default: no filtering. Slack overrides
        for channel / command / keyword."""
        return True


class PollingTrigger(TriggerHandler):
    """Pull-driven trigger. A background loop ticks ``tick()`` per
    active row at the cadence the row defines."""

    @abstractmethod
    async def tick(self, db: AsyncSession, trigger: Trigger) -> int:
        """Run one poll pass. Implementation responsibilities:

          1. Read ``trigger.poll_cursor`` to know where it left off.
          2. Fetch new events from the external source.
          3. For each, enqueue a workflow run via the shared
             dispatcher (``_dispatch.enqueue_workflow_run``).
          4. Persist the advanced ``poll_cursor`` +
             ``last_polled_at`` (caller commits).
          5. On error, stamp ``trigger.last_error`` and return
             whatever count was achieved — partial progress survives.

        Returns the number of runs dispatched this tick."""


__all__ = ["TriggerHandler", "WebhookTrigger", "PollingTrigger"]
