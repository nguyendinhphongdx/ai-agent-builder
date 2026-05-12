"""Audit log query endpoints.

Two surfaces:

  /api/admin/audit         platform-staff cross-org view (moderator+).
                           Mounted on the admin router so it inherits
                           the existing role gate.

  /api/orgs/{id}/audit     org-admin view of their own org. Same
                           filters; just scoped down.

CSV export available on both via ``?format=csv``. Streaming so a
multi-million-row export doesn't load the whole result into memory.
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.user import User
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.ops.audit import service as audit_service
from app.platform.db.session import get_db

# Two separate routers — one for the admin namespace (staff view),
# one for the per-org namespace (tenant view). Same handler shape;
# the org-scoped router pins organization_id from the URL.
admin_router = APIRouter(prefix="/audit", tags=["admin:audit"])
org_router = APIRouter(tags=["audit"])


# ─── Schemas ───────────────────────────────────────────────────────


class AuditLogRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID | None
    workspace_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    actor_type: str
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    user_agent: str | None
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


def _to_row(r: AuditLog) -> AuditLogRow:
    return AuditLogRow(
        id=r.id,
        organization_id=r.organization_id,
        workspace_id=r.workspace_id,
        actor_user_id=r.actor_user_id,
        actor_type=r.actor_type,
        action=r.action,
        resource_type=r.resource_type,
        resource_id=r.resource_id,
        ip_address=str(r.ip_address) if r.ip_address else None,
        user_agent=r.user_agent,
        data=r.data or {},
        created_at=r.created_at,
    )


# ─── Shared query helper ───────────────────────────────────────────


async def _list_audit(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID | None,
    workspace_id: uuid.UUID | None,
    actor_user_id: uuid.UUID | None,
    action: str | None,
    action_prefix: str | None,
    resource_type: str | None,
    resource_id: str | None,
    since: datetime | None,
    until: datetime | None,
    limit: int,
    offset: int,
) -> list[AuditLog]:
    return await audit_service.list_for_org(
        db,
        organization_id=organization_id,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        action_prefix=action_prefix,
        resource_type=resource_type,
        resource_id=resource_id,
        since=since,
        until=until,
        limit=limit,
        offset=offset,
    )


_CSV_COLUMNS = (
    "created_at",
    "action",
    "actor_type",
    "actor_user_id",
    "organization_id",
    "workspace_id",
    "resource_type",
    "resource_id",
    "ip_address",
    "user_agent",
    "metadata",
)


def _csv_stream(rows: list[AuditLog]):
    """Yield CSV bytes line-by-line so large exports don't materialise
    in memory. The audit log can grow fast — generators matter."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_CSV_COLUMNS)
    yield buf.getvalue().encode("utf-8")
    buf.seek(0)
    buf.truncate(0)

    for r in rows:
        writer.writerow(
            [
                r.created_at.isoformat(),
                r.action,
                r.actor_type,
                str(r.actor_user_id or ""),
                str(r.organization_id or ""),
                str(r.workspace_id or ""),
                r.resource_type or "",
                r.resource_id or "",
                str(r.ip_address) if r.ip_address else "",
                (r.user_agent or "")[:500],
                # metadata as JSON string — easier for spreadsheets than nested cells
                _json_dumps_compact(r.data or {}),
            ]
        )
        yield buf.getvalue().encode("utf-8")
        buf.seek(0)
        buf.truncate(0)


def _json_dumps_compact(d: dict[str, Any]) -> str:
    import json

    return json.dumps(d, separators=(",", ":"), default=str)


# ─── Admin (platform staff) ────────────────────────────────────────


@admin_router.get("")
async def admin_list_audit(
    organization_id: uuid.UUID | None = Query(default=None),
    workspace_id: uuid.UUID | None = Query(default=None),
    actor_user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    action_prefix: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    format: str | None = Query(default=None, pattern="^(csv)$"),
    db: AsyncSession = Depends(get_db),
):
    """Platform-staff cross-tenant audit query.

    Inherits moderator+ from the parent /admin router; no further
    role gating needed.
    """
    rows = await _list_audit(
        db,
        organization_id=organization_id,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        action_prefix=action_prefix,
        resource_type=resource_type,
        resource_id=resource_id,
        since=since,
        until=until,
        # CSV export uses a larger ceiling — but still capped to keep
        # the response time bounded.
        limit=min(limit, 500) if format != "csv" else min(limit * 50, 5000),
        offset=offset,
    )
    if format == "csv":
        return StreamingResponse(
            _csv_stream(rows),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="audit-{datetime.utcnow().strftime("%Y%m%d")}.csv"'
                ),
            },
        )
    return [_to_row(r).model_dump() for r in rows]


# ─── Org-scoped (tenant admin) ─────────────────────────────────────


@org_router.get("/orgs/{org_id}/audit")
async def org_list_audit(
    org_id: uuid.UUID,
    workspace_id: uuid.UUID | None = Query(default=None),
    actor_user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None),
    action_prefix: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    format: str | None = Query(default=None, pattern="^(csv)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Org-admin view of their own org's audit trail.

    Permission: same as other ``/api/orgs/{id}/*`` endpoints — admin+
    role in any workspace under the org. Reuses the existing helper
    from the SSO admin router."""
    from app.modules.identity.auth.sso.router import _require_org_admin

    await _require_org_admin(db, current_user, org_id)

    rows = await _list_audit(
        db,
        organization_id=org_id,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        action_prefix=action_prefix,
        resource_type=resource_type,
        resource_id=resource_id,
        since=since,
        until=until,
        limit=min(limit, 500) if format != "csv" else min(limit * 50, 5000),
        offset=offset,
    )
    if format == "csv":
        return StreamingResponse(
            _csv_stream(rows),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="audit-{org_id}-{datetime.utcnow().strftime("%Y%m%d")}.csv"'
                ),
            },
        )
    return [_to_row(r).model_dump() for r in rows]
