"""Notification service — mint socket tokens + relay events via dispatcher.

Socket emits go through ``/dispatch/exchange`` (target=socket). The
dispatcher injects the ``x-api-secret`` header on its own (configured
under ``services.socket.header`` in ``services/dispatcher/src/config/
routes.json``); the backend doesn't carry that secret.
"""

from datetime import timedelta

from app.modules.identity.auth.service import create_token
from app.platform.dispatcher_client import dispatcher


async def _emit(path: str, body: dict) -> None:
    """Forward to a socket /emit endpoint via dispatcher."""
    await dispatcher.call("socket", path, body=body, timeout=5.0)


def create_socket_token(user_id: str, rooms: list[str] | None = None) -> str:
    """Mint short-lived JWT for socket handshake (60s, type=socket)."""
    data = {"sub": user_id, "type": "socket"}
    if rooms:
        data["rooms"] = rooms
    return create_token(data, timedelta(seconds=60))


async def notify_user(user_id: str, event: str, payload: dict) -> None:
    """Send event to a specific user via socket service."""
    await _emit("/emit", body={"userId": user_id, "event": event, "payload": payload})


async def notify_room(room: str, event: str, payload: dict) -> None:
    """Send event to a room via socket service."""
    await _emit("/emit/room", body={"room": room, "event": event, "payload": payload})


async def broadcast(event: str, payload: dict) -> None:
    """Send event to all connected users via socket service."""
    await _emit("/emit/broadcast", body={"event": event, "payload": payload})
