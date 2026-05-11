"""Audit log writer + query helpers.

Keep the writer **non-blocking on the caller's happy path**: the
audit row is added to the caller's existing session and flushed
with the rest of the transaction. We don't want to spawn a background
task for every event (would race with the main commit + lose
correlation with the actual change). When the surrounding txn
rolls back the audit row goes with it — which is correct, since
the change never happened.

For events without a request context (cron tick, scheduler), pass
``actor_type=ACTOR_SYSTEM`` and a fresh session.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import current_user_id_or_none, current_workspace_id_or_none
from app.models.audit_log import (
    ACTOR_API_TOKEN,
    ACTOR_SCIM,
    ACTOR_SSO,
    ACTOR_SYSTEM,
    ACTOR_USER,
    AuditLog,
)
from app.models.workspace import Workspace

logger = logging.getLogger("agentforge")


# ─── Write ────────────────────────────────────────────────────────


async def log_event(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str | None = None,
    resource_id: str | uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_type: str = ACTOR_USER,
    organization_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    request: Request | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an audit row to the caller's session.

    Auto-fills missing fields from request context:
      - ``actor_user_id`` defaults to :func:`current_user_id_or_none`
      - ``workspace_id`` defaults to :func:`current_workspace_id_or_none`
      - ``organization_id`` resolves from workspace_id when omitted
      - ``ip_address`` + ``user_agent`` come from ``request`` if given

    The row is flushed but NOT committed — the caller's transaction
    decides whether it persists. If the surrounding business change
    rolls back, so does the audit row (which is the desired behaviour
    for atomicity).
    """
    actor_user_id = actor_user_id if actor_user_id is not None else current_user_id_or_none()
    workspace_id = workspace_id if workspace_id is not None else current_workspace_id_or_none()

    # Org auto-resolved from workspace — cheaper than asking callers
    # to look it up at every event site.
    if organization_id is None and workspace_id is not None:
        organization_id = await db.scalar(
            select(Workspace.organization_id).where(Workspace.id == workspace_id)
        )

    ip_address: str | None = None
    user_agent: str | None = None
    if request is not None:
        # Honour the first hop of X-Forwarded-For for proxy deployments —
        # same logic as rate_limit._client_ip.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            ip_address = fwd.split(",", 1)[0].strip()
        elif request.client is not None:
            ip_address = request.client.host
        user_agent = request.headers.get("user-agent")
        # API-token requests get a distinct actor_type so audit consumers
        # can filter "human did X" vs "script did X".
        if actor_type == ACTOR_USER and getattr(request.state, "api_token", None) is not None:
            actor_type = ACTOR_API_TOKEN

    row = AuditLog(
        organization_id=organization_id,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent[:8000] if user_agent else None,
        data=metadata or {},
    )
    db.add(row)
    try:
        await db.flush()
    except Exception:
        # Never let an audit failure break the underlying change —
        # we'd rather log silently than refuse a successful operation.
        logger.exception("audit: failed to write log row for action=%s", action)
        # Don't re-raise — drop the row and let the txn proceed without it.
        return row
    return row


# Convenience alias for the most common shape — call sites read better
# as ``await audit.log(...)`` than ``await audit.log_event(...)``.
log = log_event


# ─── Query (admin-side) ───────────────────────────────────────────


async def list_for_org(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    action: str | None = None,
    action_prefix: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    """Newest-first query. All filters are optional + AND-combined.

    ``action_prefix`` matches the dotted-action style — pass
    ``"workspace.member."`` to get every membership event without
    enumerating each one.
    """
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if organization_id is not None:
        stmt = stmt.where(AuditLog.organization_id == organization_id)
    if workspace_id is not None:
        stmt = stmt.where(AuditLog.workspace_id == workspace_id)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if action_prefix is not None:
        stmt = stmt.where(AuditLog.action.like(f"{action_prefix}%"))
    if resource_type is not None:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if resource_id is not None:
        stmt = stmt.where(AuditLog.resource_id == resource_id)
    if since is not None:
        stmt = stmt.where(AuditLog.created_at >= since)
    if until is not None:
        stmt = stmt.where(AuditLog.created_at < until)
    stmt = stmt.offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


# ─── Retention ────────────────────────────────────────────────────


async def purge_older_than(
    db: AsyncSession, *, days: int, organization_id: uuid.UUID | None = None
) -> int:
    """Hard-delete audit rows older than ``days``. Use from a scheduled
    job. ``organization_id=None`` purges across the platform.

    Returns the number of rows deleted.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = delete(AuditLog).where(AuditLog.created_at < cutoff)
    if organization_id is not None:
        stmt = stmt.where(AuditLog.organization_id == organization_id)
    result = await db.execute(stmt)
    await db.commit()
    return int(result.rowcount or 0)


__all__ = [
    "log_event",
    "log",
    "list_for_org",
    "purge_older_than",
    "ACTOR_USER",
    "ACTOR_API_TOKEN",
    "ACTOR_SCIM",
    "ACTOR_SSO",
    "ACTOR_SYSTEM",
]
