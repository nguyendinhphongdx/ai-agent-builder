"""Trigger handler registry — Registry pattern.

Single source of truth mapping ``type`` string → handler instance.
Handlers are stateless singletons; the dict is built once at import
time.

Adding a 6th type:
  1. Subclass ``WebhookTrigger`` or ``PollingTrigger`` in a new
     ``<type>/handler.py``.
  2. Add an entry below.
  3. (For polling) Update ``app.background.<loop>`` if it needs a
     new periodic sweep entry.

Lookups go through ``get_handler(type)``; ``unknown_type`` raises so
the router returns 422 rather than silently no-op.
"""
from __future__ import annotations

from app.models.trigger import (
    TRIGGER_TYPE_DISCORD,
    TRIGGER_TYPE_EMAIL,
    TRIGGER_TYPE_SCHEDULED,
    TRIGGER_TYPE_SLACK,
    TRIGGER_TYPE_TEAMS,
)
from app.modules.runtime.triggers._base import TriggerHandler
from app.modules.runtime.triggers.discord.handler import DiscordHandler
from app.modules.runtime.triggers.email.handler import EmailHandler
from app.modules.runtime.triggers.scheduled.handler import ScheduledHandler
from app.modules.runtime.triggers.slack.handler import SlackHandler
from app.modules.runtime.triggers.teams.handler import TeamsHandler

TRIGGER_HANDLERS: dict[str, TriggerHandler] = {
    TRIGGER_TYPE_SLACK: SlackHandler(),
    TRIGGER_TYPE_TEAMS: TeamsHandler(),
    TRIGGER_TYPE_DISCORD: DiscordHandler(),
    TRIGGER_TYPE_EMAIL: EmailHandler(),
    TRIGGER_TYPE_SCHEDULED: ScheduledHandler(),
}


class UnknownTriggerType(ValueError):
    """Raised when a caller asks for a handler that isn't registered.
    Routers translate to 422; services bubble up."""


def get_handler(trigger_type: str) -> TriggerHandler:
    handler = TRIGGER_HANDLERS.get(trigger_type)
    if handler is None:
        raise UnknownTriggerType(
            f"No handler registered for trigger type {trigger_type!r}"
        )
    return handler


def known_types() -> list[str]:
    """Stable iteration order for the picker UI."""
    return list(TRIGGER_HANDLERS.keys())


__all__ = [
    "TRIGGER_HANDLERS",
    "UnknownTriggerType",
    "get_handler",
    "known_types",
]
