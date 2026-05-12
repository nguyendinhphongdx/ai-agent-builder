"""Persistent inbox layer on top of the socket relay.

Two-layer model:
  - This file: the inbox source of truth — DB rows that survive
    sessions, drive the bell-icon, and let users browse history.
  - service.py: the SOCKET RELAY — fire-and-forget WS pushes that
    deliver real-time updates ON TOP of the persisted rows.

``notify(...)`` does both: writes the row, fans out via socket.
Callers that want push-only (no inbox row) keep using
``service.notify_user`` directly.

Channel routing respects ``notification_preferences``:
  - in_app   → always write the DB row (so history isn't gappy);
                only emit WS event when in_app=True.
  - email    → optional; future hook calls the mail service.
  - push     → optional; future hook calls FCM/web-push.
For v1 we wire in-app only — the preference rows + columns are in
place so adding channels later is a non-breaking change.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPreference
from app.platform.context import current_user_id_or_none

logger = logging.getLogger("agentforge")


# ─── Reads ─────────────────────────────────────────────────────────


async def list_for_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    unread_only: bool = False,
) -> Sequence[Notification]:
    """Paginated inbox read. Newest first."""
    stmt = (
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(desc(Notification.created_at))
        .limit(limit)
        .offset(offset)
    )
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return (await db.execute(stmt)).scalars().all()


async def unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Count for the bell-icon badge. Partial index covers this."""
    return int(
        (
            await db.scalar(
                select(func.count(Notification.id)).where(
                    Notification.user_id == user_id,
                    Notification.read_at.is_(None),
                )
            )
        )
        or 0
    )


# ─── Mutations ─────────────────────────────────────────────────────


async def mark_read(
    db: AsyncSession, user_id: uuid.UUID, notification_id: uuid.UUID
) -> bool:
    """Stamp read_at on one row. Returns True iff a row was updated."""
    row = await db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    if row is None:
        return False
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        await db.flush()
    return True


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Bulk-read every unread row. Returns the row count flipped."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    return int(result.rowcount or 0)


# ─── Preferences ───────────────────────────────────────────────────


async def get_preferences(
    db: AsyncSession, user_id: uuid.UUID
) -> Sequence[NotificationPreference]:
    return (
        await db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id
            )
        )
    ).scalars().all()


async def get_preference(
    db: AsyncSession, user_id: uuid.UUID, type_: str
) -> NotificationPreference | None:
    return await db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.type == type_,
        )
    )


async def upsert_preference(
    db: AsyncSession,
    user_id: uuid.UUID,
    type_: str,
    *,
    in_app: bool | None = None,
    email: bool | None = None,
    push: bool | None = None,
) -> NotificationPreference:
    pref = await get_preference(db, user_id, type_)
    if pref is None:
        pref = NotificationPreference(
            user_id=user_id,
            type=type_,
            in_app=True if in_app is None else in_app,
            email=True if email is None else email,
            push=False if push is None else push,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(pref)
    else:
        if in_app is not None:
            pref.in_app = in_app
        if email is not None:
            pref.email = email
        if push is not None:
            pref.push = push
        pref.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return pref


# ─── Write + fan-out ───────────────────────────────────────────────


async def notify(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str | None = None,
    link_url: str | None = None,
    workspace_id: uuid.UUID | None = None,
    extra: dict[str, Any] | None = None,
) -> Notification | None:
    """Persist a notification + fan out via the configured channels.

    Returns the row, or None when the write failed (we swallow so
    a logging-flavoured failure doesn't poison the surrounding
    business path).

    Channel routing reads ``notification_preferences`` per (user,
    type). Missing prefs default to: in_app=True, email=True,
    push=False. The default mirrors what most SaaS products do —
    spam users in-app and via email; push only when they opt in.
    """
    now = datetime.now(timezone.utc)
    row = Notification(
        user_id=user_id,
        workspace_id=workspace_id,
        type=type,
        title=title,
        body=body,
        link_url=link_url,
        extra=extra or {},
        created_at=now,
    )
    try:
        db.add(row)
        await db.flush()
    except Exception:  # noqa: BLE001
        logger.exception("notify: insert failed for user=%s type=%s", user_id, type)
        return None

    pref = await get_preference(db, user_id, type)
    want_in_app = pref.in_app if pref is not None else True

    if want_in_app:
        # Real-time WS push so the bell icon updates instantly.
        # Wrapped in try because the socket service can be down
        # without breaking the inbox row write.
        try:
            from app.modules.notifications import service as socket_service

            await socket_service.notify_user(
                str(user_id),
                event="notification",
                payload={
                    "id": str(row.id),
                    "type": row.type,
                    "title": row.title,
                    "body": row.body,
                    "link_url": row.link_url,
                    "extra": row.extra,
                    "created_at": now.isoformat(),
                },
            )
        except Exception:  # noqa: BLE001
            logger.debug(
                "notify: socket push failed (will rely on poll)", exc_info=True
            )

    # Email + push channels land later (Block 3 wiring).
    return row


async def notify_current_user(
    db: AsyncSession,
    *,
    type: str,
    title: str,
    body: str | None = None,
    link_url: str | None = None,
    extra: dict[str, Any] | None = None,
) -> Notification | None:
    """Convenience: read user from the request ContextVar.

    Use only inside request handlers. Background tasks must pass
    user_id explicitly via ``notify``.
    """
    user_id = current_user_id_or_none()
    if user_id is None:
        return None
    return await notify(
        db,
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link_url=link_url,
        extra=extra,
    )
