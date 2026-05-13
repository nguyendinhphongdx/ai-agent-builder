---
title: Domain events
domain: backend
---

# Domain events

In-process pub/sub between services and the side effects they trigger.
Lets a service announce *what happened* (an invitation was created, a
user logged in) without naming the listeners that need to react
(send notification, write audit, increment usage counter).

## Why

Before the bus, services called notifications/audit/dispatcher inline:

```python
# ❌ tight coupling: workspaces service knows about notifications
async def create_invitation(...):
    inv = WorkspaceInvitation(...)
    db.add(inv); await db.flush()
    await _notify_invitee_if_user(...)   # what if it fails?
    return inv
```

Three problems with that style:

1. **Failures cascade.** A flaky notification breaks the create call.
2. **Tests fight the side effects.** Mocking notifications.inbox just
   to test invitation creation is unrelated busywork.
3. **Adding a 4th side effect = touching the service** every time.

With the bus, the service stays focused on its aggregate:

```python
# ✅ emit + let listeners do their thing
async def create_invitation(...):
    inv = WorkspaceInvitation(...)
    db.add(inv); await db.flush()
    await bus.emit(WorkspaceInvitationCreated(
        invitation_id=inv.id,
        workspace_id=inv.workspace_id,
        invited_email=inv.email,
    ))
    return inv
```

## When to emit (and when NOT)

**Emit when** the side effect is **observation** of business state
change — analytics, audit, in-app notification, derived counters,
search index refresh.

**Don't emit when**:

- The caller needs the result. Events return nothing. If the workspace
  router needs the invitation row back, the service still returns it.
- You need a transactional retry. Events fire in the request scope and
  are best-effort per listener. For durable side-effects (charge a
  card, hit a third-party API with retries), enqueue an explicit job
  via `app.platform.dispatcher_client`.
- You need strict ordering across processes. The bus is one process.

## Defining an event

Events live in `app/platform/events/types.py` or — for module-local
events that no other bucket needs to know about — under the module's
own folder. Subclass `DomainEvent`:

```python
from dataclasses import dataclass
from uuid import UUID
from app.platform.events import DomainEvent

@dataclass(frozen=True, kw_only=True)
class WorkspaceInvitationCreated(DomainEvent):
    invitation_id: UUID
    workspace_id: UUID
    invited_email: str
    inviter_id: UUID
```

Rules:

- Frozen, kw-only — adding a field is backward-compatible, listeners
  can never mutate the event mid-flight.
- Carry **identifiers + primitives only**, not ORM rows. Listeners
  re-fetch from DB if they need entity state. Keeps events
  serialisable and forces listener side-effect isolation.
- Name in past tense: `*Created`, `*Updated`, `*LoggedIn`,
  `*Cancelled`. Events are facts, not commands.

## Listening to events

Listeners live next to the side effect they own — usually in a
`listeners.py` file at the top of the module that performs the work:

```
modules/runtime/notifications/listeners.py
modules/ops/audit/listeners.py
modules/commerce/usage/listeners.py
```

The pattern:

```python
# modules/ops/audit/listeners.py
from app.platform.events import bus
from app.platform.events.types import WorkspaceInvitationCreated

from app.modules.ops.audit.service import log_event

@bus.on(WorkspaceInvitationCreated)
async def _log_invitation_audit(event: WorkspaceInvitationCreated) -> None:
    await log_event(
        action="workspace.invitation.created",
        actor_id=event.inviter_id,
        target_id=event.invitation_id,
    )
```

To make the listener register at startup, import the module once during
app boot. A cheap way: add it to the module's `__init__.py`:

```python
# modules/ops/audit/__init__.py
from app.modules.ops.audit import listeners  # noqa: F401 — register handlers
```

## Semantics

- `bus.emit(event)` awaits handlers **sequentially in registration
  order**. Side-effect ordering is deterministic.
- A handler raising never propagates: the bus logs the exception with
  `event_id` + handler qualname and continues. One bad listener
  doesn't break peers or the emitter.
- Listeners run inside the request's ContextVar scope — they see
  `current_user_id()` and the active workspace without re-threading.
- For background tasks that emit after the request returns, wrap with
  `run_in_request_context*` from `app.platform.context` to keep the
  ContextVar intact.

## Testing

Use a fresh `EventBus()` per test rather than the module singleton:

```python
def test_my_thing(bus):
    seen = []

    @bus.on(ThingHappened)
    async def capture(e): seen.append(e)

    await my_service(bus=bus, ...)
    assert seen == [...]
```

The module-level `bus` is fine for code that runs the real app; tests
isolate to keep subscriptions from leaking across cases.

## Migration plan

These call sites are first in line to convert to events (Sprint 2):

| Service | Inline call | New event |
|---|---|---|
| `workspaces.service.create_invitation` | `_notify_invitee_if_user` | `WorkspaceInvitationCreated` |
| `workspaces.service.accept_invitation` | inviter inbox ping | `WorkspaceInvitationAccepted` |
| `auth.router.login` | `audit.log_event` x2 | `UserLoggedIn` / `UserLoginFailed` |
| `auth.router.password_change` | token-version bump notifications | `UserPasswordChanged` |
