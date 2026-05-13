"""In-process domain event bus.

Lets a service announce *what happened* (e.g. "a workspace invitation
was created") without naming the side-effects that need to run
(send inbox notification, write audit log, increment usage counter…).
Listeners subscribe to event classes; ``bus.emit(event)`` awaits all
of them in registration order.

Why in-process and not Redis / RabbitMQ:

* Listeners run in the same request/task — they see the same
  ContextVar (current user, workspace, org), the same DB session if
  passed explicitly, and exceptions bubble for the request to retry.
* Failures in one listener don't break the emitter or peers — the bus
  logs + continues so audit telemetry never breaks billing.
* When a side-effect *needs* to outlive the request (cross-process
  fan-out, durable retries), use the existing ``dispatcher_client`` to
  enqueue an explicit job — events are for orchestration, not queues.

Usage::

    from app.platform.events import bus, DomainEvent

    @dataclass(frozen=True, kw_only=True)
    class WorkspaceInvitationCreated(DomainEvent):
        invitation_id: UUID
        workspace_id: UUID
        invited_email: str

    @bus.on(WorkspaceInvitationCreated)
    async def _notify_invitee(event: WorkspaceInvitationCreated) -> None:
        ...

    # In the service:
    await bus.emit(WorkspaceInvitationCreated(
        invitation_id=inv.id,
        workspace_id=ws.id,
        invited_email=email,
    ))

See ``docs/backend/events.md`` for the migration guide.
"""

from app.platform.events.bus import EventBus, bus
from app.platform.events.types import DomainEvent

__all__ = ["DomainEvent", "EventBus", "bus"]
