"""Quota state + enforcement guards.

Quota is enforced *per organization*, computed by summing all the
org's workspaces in the current billing period. Period boundaries:

  - Live Stripe subscription → ``current_period_start/end`` from it.
  - No subscription / canceled  → rolling 30 days back from now.

Enforcement rules:
  - tokens_used >= tokens_limit  → ``QuotaExceeded`` raised IFF the
                                   plan has no metered overage price
                                   (free tier blocks; metered tiers
                                   bill overage and continue).
  - kb_used    >= kb_limit       → same logic, separate counter.

Callers wire this in at the cheap-to-fail boundary: chat SSE checks
tokens before starting the stream, retriever checks kb_queries
before the SQL hit. Inside cron jobs / workflow runs we still call
it so a runaway loop doesn't burn quota without warning.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_subscription import LIVE_STATUSES, OrgSubscription
from app.models.workspace import Workspace
from app.modules.commerce.payments.subscriptions import service as billing_service
from app.modules.commerce.payments.subscriptions.plans import Plan
from app.modules.commerce.usage import service as usage_service
from app.platform.context import current_workspace_id_or_none


class QuotaExceeded(HTTPException):
    """402 Payment Required — standard for usage-based billing limits.

    ``detail`` is structured so FE can render a plan-specific
    upgrade prompt without re-fetching billing state.
    """

    def __init__(self, kind: str, used: int, limit: int, plan_code: str):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "quota_exceeded",
                "kind": kind,
                "used": used,
                "limit": limit,
                "plan": plan_code,
            },
        )


@dataclass
class QuotaState:
    plan: Plan
    tokens_used: int
    tokens_limit: int
    kb_used: int
    kb_limit: int
    period_start: datetime
    period_end: datetime | None
    # When True, going over quota → soft (the usage reporter ships
    # overage to Stripe and the org gets billed). When False, hard
    # block via QuotaExceeded.
    has_overage_pricing: bool

    def _over(self, used: int, limit: int) -> bool:
        return limit > 0 and used >= limit

    @property
    def tokens_over(self) -> bool:
        return self._over(self.tokens_used, self.tokens_limit)

    @property
    def kb_over(self) -> bool:
        return self._over(self.kb_used, self.kb_limit)


async def _resolve_org_and_period(
    db: AsyncSession, workspace_id: uuid.UUID
) -> tuple[uuid.UUID | None, OrgSubscription | None, datetime, datetime | None]:
    """Look up the org id + (optional) live subscription + period
    window for ``workspace_id``. Returns (None, None, since, None)
    when the workspace has no org binding (legacy data)."""
    org_id = await db.scalar(
        select(Workspace.organization_id).where(Workspace.id == workspace_id)
    )
    if org_id is None:
        # Fall back to rolling 30d window on the workspace itself.
        return None, None, datetime.now(timezone.utc) - timedelta(days=30), None

    sub = await billing_service.get_subscription(db, org_id)
    if sub is not None and sub.status in LIVE_STATUSES and sub.current_period_start:
        return org_id, sub, sub.current_period_start, sub.current_period_end

    # No live sub → rolling 30d. Matches what the billing dashboard
    # surfaces when there's no Stripe subscription yet.
    since = datetime.now(timezone.utc) - timedelta(days=30)
    return org_id, sub, since, None


async def get_quota_state(
    db: AsyncSession, workspace_id: uuid.UUID
) -> QuotaState:
    """Compute the current quota usage / limit pair for a workspace.

    Aggregates across every workspace in the org (not just the
    requesting workspace) so cross-workspace usage in the same org
    correctly counts against the shared plan.
    """
    org_id, sub, since, until = await _resolve_org_and_period(db, workspace_id)

    if org_id is None:
        plan = await billing_service.effective_plan_for_org(db, uuid.uuid4())  # → free
    else:
        plan = await billing_service.effective_plan_for_org(db, org_id)

    # Sum across all workspaces in the org.
    if org_id is not None:
        workspace_ids = list(
            (
                await db.execute(
                    select(Workspace.id).where(Workspace.organization_id == org_id)
                )
            ).scalars()
        )
    else:
        workspace_ids = [workspace_id]

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

    has_overage = bool(sub and sub.stripe_metered_item_id) or bool(
        plan.stripe_metered_price_id()
    )
    return QuotaState(
        plan=plan,
        tokens_used=tokens_used,
        tokens_limit=plan.monthly_llm_tokens,
        kb_used=kb_used,
        kb_limit=plan.monthly_kb_queries,
        period_start=since,
        period_end=until,
        has_overage_pricing=has_overage,
    )


async def enforce_tokens(db: AsyncSession, workspace_id: uuid.UUID | None = None) -> None:
    """Raise QuotaExceeded(kind="tokens", …) when the org is over its
    token cap and lacks a metered overage price. No-op otherwise.

    ``workspace_id`` defaults to the request's active workspace via
    the ContextVar. Background jobs that don't have a request scope
    should pass it explicitly.
    """
    workspace_id = workspace_id or current_workspace_id_or_none()
    if workspace_id is None:
        return  # No tenant scope → nothing to enforce against.
    state = await get_quota_state(db, workspace_id)
    if state.tokens_over and not state.has_overage_pricing:
        raise QuotaExceeded(
            "tokens", state.tokens_used, state.tokens_limit, state.plan.code
        )


async def enforce_kb_queries(
    db: AsyncSession, workspace_id: uuid.UUID | None = None
) -> None:
    """Mirror of ``enforce_tokens`` for the KB-query counter."""
    workspace_id = workspace_id or current_workspace_id_or_none()
    if workspace_id is None:
        return
    state = await get_quota_state(db, workspace_id)
    if state.kb_over and not state.has_overage_pricing:
        raise QuotaExceeded(
            "kb_queries", state.kb_used, state.kb_limit, state.plan.code
        )
