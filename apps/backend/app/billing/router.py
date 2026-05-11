"""Billing API — plan catalogue + subscription read endpoints.

  GET  /api/billing/plans          — list self-serve plans for the picker
  GET  /api/billing/subscription   — current plan + period + usage vs quota

Mutating endpoints (Checkout session creation, portal session,
plan switch) land in Block 2 once the Stripe client wrapper is in.
Permission gate: ``billing.manage`` — same as the usage dashboard.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import service as billing_service
from app.billing.plans import PLAN_FREE, get_plan, self_serve_plans
from app.billing.schemas import (
    BillingOverview,
    PlanInfo,
    QuotaUsage,
    SubscriptionInfo,
)
from app.context import current_workspace_id_or_none
from app.db.session import get_db
from app.models.workspace import Workspace
from app.permissions import catalogue as P
from app.usage import service as usage_service
from app.workspaces.permissions import require_active_permission

router = APIRouter(prefix="/billing", tags=["billing"])


# ─── Helpers ───────────────────────────────────────────────────────


def _plan_info(plan) -> PlanInfo:
    return PlanInfo(
        code=plan.code,
        name=plan.name,
        monthly_llm_tokens=plan.monthly_llm_tokens,
        monthly_kb_queries=plan.monthly_kb_queries,
        max_workspaces=plan.max_workspaces,
        max_members=plan.max_members,
        features=plan.features,
        is_self_serve=plan.is_self_serve(),
    )


def _quota(used: int, limit: int) -> QuotaUsage:
    if limit <= 0:
        # Unlimited — chart shows used count with 0% bar so the UI
        # can still render but doesn't trigger the "near limit" hint.
        return QuotaUsage(used=used, limit=0, pct=0.0)
    pct = min(100.0, (used / limit) * 100.0)
    return QuotaUsage(used=used, limit=limit, pct=pct)


async def _resolve_org_id(db: AsyncSession):
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="no_active_workspace"
        )
    org_id = await db.scalar(
        select(Workspace.organization_id).where(Workspace.id == workspace_id)
    )
    if org_id is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return org_id


# ─── Endpoints ─────────────────────────────────────────────────────


@router.get("/plans", response_model=list[PlanInfo])
async def list_plans():
    """Self-serve plans for the upgrade picker.

    Public-ish: no auth required so the marketing site can embed the
    same data. Stays inside the API_PREFIX so CORS rules apply.
    """
    return [_plan_info(p) for p in self_serve_plans()]


@router.get("/subscription", response_model=BillingOverview)
async def get_subscription(
    _: Any = Depends(require_active_permission(P.BILLING_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Combined plan + period + quota usage for the billing page.

    One round-trip drives the whole settings screen — the FE can
    render the "you are on", "renews on", and progress bars from
    this single payload.
    """
    org_id = await _resolve_org_id(db)

    plan = await billing_service.effective_plan_for_org(db, org_id)
    sub = await billing_service.get_subscription(db, org_id)

    # Period — Stripe defines it. If no live sub, we fall back to a
    # rolling 30d window so the quota dashboard still has a range.
    if sub and sub.current_period_start:
        since = sub.current_period_start
        until = sub.current_period_end
        status_str = sub.status
        cancel_eop = sub.cancel_at_period_end
        has_sub = True
    else:
        from datetime import datetime, timedelta, timezone
        since = datetime.now(timezone.utc) - timedelta(days=30)
        until = None
        status_str = "none" if plan.code == PLAN_FREE else "active"
        cancel_eop = False
        has_sub = False

    # Aggregate token usage across every workspace in the org. We can
    # leverage usage_service.workspace_totals with a custom filter —
    # for v1 we sum per-workspace and combine, since the usage tables
    # are per-workspace indexed. Acceptable: each org has at most a
    # handful of workspaces in practice.
    workspace_ids = list(
        (
            await db.execute(
                select(Workspace.id).where(Workspace.organization_id == org_id)
            )
        ).scalars()
    )

    tokens_used = 0
    kb_used = 0
    for ws_id in workspace_ids:
        totals = await usage_service.workspace_totals(
            db, ws_id, since=since, until=until
        )
        tokens_used += totals.get("tokens") or 0
        kb_used += await usage_service.workspace_event_count(
            db, ws_id, event_type="kb.query", since=since, until=until
        )

    return BillingOverview(
        subscription=SubscriptionInfo(
            plan=_plan_info(plan),
            status=status_str,
            current_period_start=since,
            current_period_end=until,
            cancel_at_period_end=cancel_eop,
            has_stripe_subscription=has_sub,
        ),
        tokens=_quota(tokens_used, plan.monthly_llm_tokens),
        kb_queries=_quota(kb_used, plan.monthly_kb_queries),
    )
