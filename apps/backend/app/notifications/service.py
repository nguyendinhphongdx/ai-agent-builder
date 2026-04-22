"""Notification service — mint socket tokens + relay events via dispatcher.

Socket emits go through the dispatcher `/dispatch/exchange` endpoint
(target=socket). Failures are silently swallowed at the dispatcher-client
layer so callers never need to worry about a flaky socket service.
"""

from datetime import timedelta

from app.auth.service import create_token
from app.dispatcher_client import dispatcher


def create_socket_token(user_id: str, rooms: list[str] | None = None) -> str:
    """Mint short-lived JWT for socket handshake (60s, type=socket)."""
    data = {"sub": user_id, "type": "socket"}
    if rooms:
        data["rooms"] = rooms
    return create_token(data, timedelta(seconds=60))


async def notify_user(user_id: str, event: str, payload: dict) -> None:
    """Send event to a specific user via socket service."""
    await dispatcher.sync(
        "socket",
        "/emit",
        body={"userId": user_id, "event": event, "payload": payload},
        timeout=5.0,
    )


async def notify_room(room: str, event: str, payload: dict) -> None:
    """Send event to a room via socket service."""
    await dispatcher.sync(
        "socket",
        "/emit/room",
        body={"room": room, "event": event, "payload": payload},
        timeout=5.0,
    )


async def broadcast(event: str, payload: dict) -> None:
    """Send event to all connected users via socket service."""
    await dispatcher.sync(
        "socket",
        "/emit/broadcast",
        body={"event": event, "payload": payload},
        timeout=5.0,
    )
