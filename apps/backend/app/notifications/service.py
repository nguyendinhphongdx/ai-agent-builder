"""Notification service - mint socket tokens + relay events to socket service."""

from datetime import timedelta

import httpx

from app.auth.service import create_token
from app.config import settings


def create_socket_token(user_id: str, rooms: list[str] | None = None) -> str:
    """Mint short-lived JWT for socket handshake (60s, type=socket)."""
    data = {"sub": user_id, "type": "socket"}
    if rooms:
        data["rooms"] = rooms
    return create_token(data, timedelta(seconds=60))


async def notify_user(user_id: str, event: str, payload: dict) -> None:
    """Send event to a specific user via socket service."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{settings.SOCKET_SERVICE_URL}/emit",
                json={"userId": user_id, "event": event, "payload": payload},
                headers={"x-api-secret": settings.SOCKET_API_SECRET},
            )
    except Exception:
        pass  # Best-effort, don't crash caller


async def notify_room(room: str, event: str, payload: dict) -> None:
    """Send event to a room via socket service."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{settings.SOCKET_SERVICE_URL}/emit/room",
                json={"room": room, "event": event, "payload": payload},
                headers={"x-api-secret": settings.SOCKET_API_SECRET},
            )
    except Exception:
        pass


async def broadcast(event: str, payload: dict) -> None:
    """Send event to all connected users via socket service."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(
                f"{settings.SOCKET_SERVICE_URL}/emit/broadcast",
                json={"event": event, "payload": payload},
                headers={"x-api-secret": settings.SOCKET_API_SECRET},
            )
    except Exception:
        pass
