"""Annotation CRUD + dashboard aggregations.

Upsert semantics: a repeat rating from the same user overwrites
the previous one, so the FE doesn't have to GET-before-PUT.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.message_annotation import MessageAnnotation
from app.platform.context import current_user_id_or_none


async def upsert_annotation(
    db: AsyncSession,
    *,
    message_id: uuid.UUID,
    rating: int,
    feedback: str | None = None,
    expected_response: str | None = None,
    tags: list[str] | None = None,
) -> MessageAnnotation:
    """Insert-or-update on (message_id, user_id).

    Looks up workspace_id by joining through messages → conversations
    so dashboard aggregations stay workspace-scoped without a
    runtime join.
    """
    user_id = current_user_id_or_none()
    if user_id is None:
        raise ValueError("no_authenticated_user")
    if rating not in (-1, 1):
        raise ValueError("rating_must_be_plus_or_minus_one")

    workspace_id = await db.scalar(
        select(Conversation.workspace_id)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Message.id == message_id)
    )

    existing = await db.scalar(
        select(MessageAnnotation).where(
            MessageAnnotation.message_id == message_id,
            MessageAnnotation.user_id == user_id,
        )
    )
    if existing is not None:
        existing.rating = rating
        if feedback is not None:
            existing.feedback = feedback
        if expected_response is not None:
            existing.expected_response = expected_response
        if tags is not None:
            existing.tags = tags
        await db.flush()
        return existing

    row = MessageAnnotation(
        message_id=message_id,
        user_id=user_id,
        workspace_id=workspace_id,
        rating=rating,
        feedback=feedback,
        expected_response=expected_response,
        tags=tags or [],
    )
    db.add(row)
    await db.flush()
    return row


async def delete_annotation(
    db: AsyncSession, message_id: uuid.UUID
) -> bool:
    """Remove the current user's annotation for ``message_id``."""
    user_id = current_user_id_or_none()
    if user_id is None:
        return False
    row = await db.scalar(
        select(MessageAnnotation).where(
            MessageAnnotation.message_id == message_id,
            MessageAnnotation.user_id == user_id,
        )
    )
    if row is None:
        return False
    await db.delete(row)
    await db.flush()
    return True


async def get_for_message(
    db: AsyncSession, message_id: uuid.UUID
) -> MessageAnnotation | None:
    """The current user's own annotation, if any."""
    user_id = current_user_id_or_none()
    if user_id is None:
        return None
    return await db.scalar(
        select(MessageAnnotation).where(
            MessageAnnotation.message_id == message_id,
            MessageAnnotation.user_id == user_id,
        )
    )


# ─── Dashboard aggregations ────────────────────────────────────────


async def workspace_totals(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    since: datetime | None = None,
) -> dict[str, Any]:
    """Up / down / total + thumbs-up rate for the dashboard hero."""
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
    rows = (
        await db.execute(
            select(
                MessageAnnotation.rating,
                func.count(MessageAnnotation.id).label("n"),
            )
            .where(
                MessageAnnotation.workspace_id == workspace_id,
                MessageAnnotation.created_at >= since,
            )
            .group_by(MessageAnnotation.rating)
        )
    ).all()
    up = next((int(r.n) for r in rows if r.rating == 1), 0)
    down = next((int(r.n) for r in rows if r.rating == -1), 0)
    total = up + down
    return {
        "up": up,
        "down": down,
        "total": total,
        "up_rate": (up / total) if total > 0 else 0.0,
        "since": since.isoformat(),
    }


async def recent_negative(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    limit: int = 50,
) -> Sequence[MessageAnnotation]:
    """Latest thumbs-down rows for the "where are we failing" table."""
    return (
        await db.execute(
            select(MessageAnnotation)
            .where(
                MessageAnnotation.workspace_id == workspace_id,
                MessageAnnotation.rating == -1,
            )
            .order_by(desc(MessageAnnotation.created_at))
            .limit(limit)
        )
    ).scalars().all()


async def top_tags(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    since: datetime | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Unnest the tags array and count usage. Top-N for the chart."""
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(days=30)
    tag = func.unnest(MessageAnnotation.tags).label("tag")
    stmt = (
        select(tag, func.count().label("n"))
        .where(
            MessageAnnotation.workspace_id == workspace_id,
            MessageAnnotation.created_at >= since,
        )
        .group_by(tag)
        .order_by(desc("n"))
        .limit(limit)
    )
    return [{"tag": r.tag, "count": int(r.n)} for r in (await db.execute(stmt)).all()]


# ─── Fine-tuning dataset export ────────────────────────────────────


async def export_jsonl_rows(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    only_negative: bool = False,
) -> list[dict[str, Any]]:
    """Build OpenAI-compatible JSONL records from annotations.

    Each row is ``{ "messages": [{"role": "user", "content": ...},
    {"role": "assistant", "content": <expected_response or
    original>}] }``. ``only_negative`` filters to thumbs-down rows
    where ``expected_response`` is set — the gold "what should
    have been said" pairs that actually move the needle.
    """
    stmt = (
        select(MessageAnnotation, Message)
        .join(Message, Message.id == MessageAnnotation.message_id)
        .where(MessageAnnotation.workspace_id == workspace_id)
    )
    if only_negative:
        stmt = stmt.where(
            MessageAnnotation.rating == -1,
            MessageAnnotation.expected_response.is_not(None),
        )

    rows = (await db.execute(stmt)).all()
    out: list[dict[str, Any]] = []
    for ann, msg in rows:
        # Look up the immediately preceding user message in the
        # same conversation. Naive — fine for v1; could JOIN-with-
        # LATERAL if this becomes hot.
        prev_user = await db.scalar(
            select(Message)
            .where(
                Message.conversation_id == msg.conversation_id,
                Message.role == "user",
                Message.created_at < msg.created_at,
            )
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        if prev_user is None:
            continue
        out.append(
            {
                "messages": [
                    {"role": "user", "content": prev_user.content},
                    {
                        "role": "assistant",
                        "content": ann.expected_response or msg.content,
                    },
                ],
                "rating": ann.rating,
                "tags": ann.tags,
            }
        )
    return out
