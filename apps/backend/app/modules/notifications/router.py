import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import get_current_user
from app.modules.notifications import inbox
from app.modules.notifications.schemas import SocketConnectionResponse
from app.modules.notifications.service import create_socket_token
from app.platform.config import settings
from app.platform.context import current_user_id
from app.platform.db.session import get_db

router = APIRouter(
    tags=["notifications"],
    dependencies=[Depends(get_current_user)],
)


# ─── Socket handshake (legacy, kept) ───────────────────────────────


@router.get("/me/socket", response_model=SocketConnectionResponse)
async def get_socket_connection():
    """Get socket URL + short-lived token for WebSocket connection."""
    user_id = current_user_id()
    rooms = [f"user:{user_id}"]
    token = create_socket_token(str(user_id), rooms)
    return SocketConnectionResponse(
        url=settings.SOCKET_PUBLIC_URL,
        token=token,
    )


# ─── Inbox (P3.5 Block 1) ──────────────────────────────────────────


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None
    link_url: str | None
    extra: dict[str, Any]
    read_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCount(BaseModel):
    count: int


class NotificationPreferenceItem(BaseModel):
    type: str
    in_app: bool
    email: bool
    push: bool


class NotificationPreferenceUpdate(BaseModel):
    in_app: bool | None = None
    email: bool | None = None
    push: bool | None = None


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user_id()
    rows = await inbox.list_for_user(
        db, user_id, limit=limit, offset=offset, unread_only=unread_only
    )
    return [NotificationResponse.model_validate(r) for r in rows]


@router.get("/notifications/unread-count", response_model=UnreadCount)
async def get_unread_count(db: AsyncSession = Depends(get_db)):
    user_id = current_user_id()
    return UnreadCount(count=await inbox.unread_count(db, user_id))


@router.post("/notifications/{notification_id}/read", status_code=204)
async def mark_one_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user_id()
    ok = await inbox.mark_read(db, user_id, notification_id)
    if not ok:
        raise HTTPException(status_code=404, detail="notification_not_found")
    await db.commit()
    return None


@router.post("/notifications/read-all")
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    user_id = current_user_id()
    n = await inbox.mark_all_read(db, user_id)
    await db.commit()
    return {"marked": n}


@router.get("/notifications/preferences", response_model=list[NotificationPreferenceItem])
async def list_preferences(db: AsyncSession = Depends(get_db)):
    user_id = current_user_id()
    prefs = await inbox.get_preferences(db, user_id)
    return [
        NotificationPreferenceItem(
            type=p.type, in_app=p.in_app, email=p.email, push=p.push
        )
        for p in prefs
    ]


@router.put(
    "/notifications/preferences/{type}",
    response_model=NotificationPreferenceItem,
)
async def update_preference(
    type: str,
    payload: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
):
    user_id = current_user_id()
    pref = await inbox.upsert_preference(
        db,
        user_id,
        type,
        in_app=payload.in_app,
        email=payload.email,
        push=payload.push,
    )
    await db.commit()
    return NotificationPreferenceItem(
        type=pref.type, in_app=pref.in_app, email=pref.email, push=pref.push
    )
