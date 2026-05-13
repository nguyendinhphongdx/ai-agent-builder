"""Base type for domain events.

Subclass with ``@dataclass(frozen=True, kw_only=True)`` and add the
fields you need — keep them small (just identifiers and primitives,
no SQLAlchemy rows). Listeners fetch the entities they need from the
DB themselves so events stay serialisable and side-effect-free.

Frozen so a listener can't mutate the event for the next listener.
Kw-only so adding a field is backward-compatible. Slotted for cheap
construction since events fire often.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """Base class for every in-process domain event.

    Concrete events should be frozen, kw-only dataclasses that subclass
    this. The two base fields are populated automatically:

    * ``event_id`` — unique per emit; useful for log correlation.
    * ``occurred_at`` — UTC timestamp at construction time.
    """

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
