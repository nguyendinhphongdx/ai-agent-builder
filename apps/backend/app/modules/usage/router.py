"""Cost / usage dashboard read endpoints.

  GET /api/usage/totals                workspace totals + period
  GET /api/usage/daily                 day-bucketed cost trend
  GET /api/usage/by-model              spend-by-model rollup

All scoped to the active workspace via the ContextVar from
``get_current_user``. Permission gated on ``billing.manage`` —
which the owner role has by default; admins can grant via custom
role for finance team members who shouldn't have full workspace
admin.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.usage import service as usage_service
from app.modules.workspaces.permissions import require_active_permission
from app.platform.context import current_workspace_id_or_none
from app.platform.db.session import get_db
from app.platform.permissions import catalogue as P

router = APIRouter(prefix="/usage", tags=["usage"])


# ─── Schemas ───────────────────────────────────────────────────────


class UsageTotals(BaseModel):
    count: int
    tokens: int
    cost_usd: float
    avg_latency_ms: float
    since: str
    until: str


class UsageDailyPoint(BaseModel):
    day: str
    count: int
    tokens: int
    cost_usd: float


class UsageModelRow(BaseModel):
    provider: str | None
    model: str | None
    count: int
    tokens: int
    cost_usd: float


# ─── Helpers ───────────────────────────────────────────────────────


def _active_workspace_or_403() -> Any:
    ws = current_workspace_id_or_none()
    if ws is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="no_active_workspace",
        )
    return ws


# ─── Endpoints ─────────────────────────────────────────────────────


@router.get("/totals", response_model=UsageTotals)
async def get_totals(
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate counts + spend + avg latency for the workspace.

    Default window: last 30 days. ``since`` / ``until`` accept ISO
    timestamps for custom ranges (e.g. month-to-date, or comparing
    last month vs this month for a billing review).
    """
    workspace_id = _active_workspace_or_403()
    data = await usage_service.workspace_totals(
        db, workspace_id, since=since, until=until
    )
    return UsageTotals(**data)


@router.get("/daily", response_model=list[UsageDailyPoint])
async def get_daily(
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """One bucket per UTC day in the window. Drives the cost chart."""
    workspace_id = _active_workspace_or_403()
    return [
        UsageDailyPoint(**row)
        for row in await usage_service.workspace_daily(
            db, workspace_id, since=since, until=until
        )
    ]


@router.get("/by-model", response_model=list[UsageModelRow])
async def get_by_model(
    since: datetime | None = Query(default=None),
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Spend per (provider, model). Sorted by cost desc so the
    biggest movers float to the top."""
    workspace_id = _active_workspace_or_403()
    return [
        UsageModelRow(**row)
        for row in await usage_service.workspace_by_model(
            db, workspace_id, since=since
        )
    ]
