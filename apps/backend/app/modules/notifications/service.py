"""Notification service — mint socket tokens + relay events via dispatcher.

Socket emits go through the dispatcher `/dispatch/exchange` endpoint
(target=socket). The socket service's `/emit*` endpoints are guarded by
`x-api-secret` — we forward the header here; the dispatcher is a dumb
passthrough so each caller controls which downstream auth to use.
"""

from datetime import timedelta

from app.modules.auth.service import create_token
from app.platform.config import settings
from app.platform.dispatcher_client import dispatcher


def _socket_headers() -> dict[str, str]:
    """Auth header forwarded by dispatcher to the socket service."""
    return {"x-api-secret": settings.SOCKET_API_SECRET}

async def _emit(path: str, body: dict) -> None:
    """Forward to a socket /emit endpoint with the shared auth header."""
    await dispatcher.call(
        "socket",
        path,
        body=body,
        headers=_socket_headers(),
        timeout=5.0,
    )

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
