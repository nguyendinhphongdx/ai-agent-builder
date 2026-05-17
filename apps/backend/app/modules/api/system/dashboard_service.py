"""Platform-admin dashboard aggregates.

Single fat endpoint feeds the ``/system/dashboard`` page. Computes
everything in parallel-ish (each block is one SQL round-trip) so the
admin sees fresh numbers without 10+ requests.

Numbers exposed here are estimates, not invoices — MRR uses the
declared ``Plan.monthly_price_cents_usd`` × live-sub count. The
authoritative ledger still lives in Stripe; this view is for
operational visibility ("are we growing? who's churning?").
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.conversation import Conversation
from app.models.org_subscription import LIVE_STATUSES, OrgSubscription
from app.models.organization import Organization
from app.models.usage_event import EVENT_KB_QUERY, EVENT_LLM_CALL, UsageEvent
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.commerce.payments.subscriptions.plans import PLANS


async def aggregate(db: AsyncSession) -> dict[str, Any]:
    """Whole-platform snapshot. ~10 small queries, ~50ms typical."""
    now = datetime.now(timezone.utc)
    month_ago = now - timedelta(days=30)
    week_ago = now - timedelta(days=7)

    # ─── Orgs ───────────────────────────────────────────────────
    orgs_total = int(await db.scalar(select(func.count()).select_from(Organization)) or 0)
    orgs_new_30d = int(
        await db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.created_at >= month_ago)
        )
        or 0
    )
    orgs_new_7d = int(
        await db.scalar(
            select(func.count())
            .select_from(Organization)
            .where(Organization.created_at >= week_ago)
        )
        or 0
    )

    # ─── Users ──────────────────────────────────────────────────
    users_total = int(await db.scalar(select(func.count()).select_from(User)) or 0)
    users_active_30d = int(
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.last_login_at >= month_ago)
        )
        or 0
    )
    users_active_7d = int(
        await db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.last_login_at >= week_ago)
        )
        or 0
    )
    activity_rate = (users_active_30d / users_total * 100) if users_total else 0.0

    # ─── Subscriptions + MRR ────────────────────────────────────
    # Effective plan per org (live sub wins, else org.plan).
    effective_plan = case(
        (OrgSubscription.status.in_(LIVE_STATUSES), OrgSubscription.plan_code),
        else_=Organization.plan,
    )
    plan_rows = (
        await db.execute(
            select(effective_plan.label("plan_code"), func.count())
            .select_from(Organization)
            .outerjoin(
                OrgSubscription,
                OrgSubscription.organization_id == Organization.id,
            )
            .group_by(effective_plan)
        )
    ).all()
    by_plan: dict[str, int] = {p or "free": int(c or 0) for p, c in plan_rows}

    mrr_usd_cents = 0
    for plan_code, count in by_plan.items():
        plan = PLANS.get(plan_code)
        if plan:
            mrr_usd_cents += plan.monthly_price_cents_usd * count

    live_subs = int(
        await db.scalar(
            select(func.count())
            .select_from(OrgSubscription)
            .where(OrgSubscription.status.in_(LIVE_STATUSES))
        )
        or 0
    )
    cancel_scheduled = int(
        await db.scalar(
            select(func.count())
            .select_from(OrgSubscription)
            .where(OrgSubscription.cancel_at_period_end.is_(True))
        )
        or 0
    )

    # ─── Hub revenue (one-time template purchases) ──────────────
    hub_paid = (
        await db.execute(
            select(
                func.coalesce(func.sum(AgentTemplatePurchase.price_paid_cents), 0),
                func.count(),
            ).where(AgentTemplatePurchase.status == "paid")
        )
    ).one()
    hub_revenue_cents = int(hub_paid[0] or 0)
    hub_purchases_total = int(hub_paid[1] or 0)

    hub_30d = (
        await db.execute(
            select(
                func.coalesce(func.sum(AgentTemplatePurchase.price_paid_cents), 0),
                func.count(),
            ).where(
                AgentTemplatePurchase.status == "paid",
                AgentTemplatePurchase.purchased_at >= month_ago,
            )
        )
    ).one()
    hub_revenue_30d_cents = int(hub_30d[0] or 0)
    hub_purchases_30d = int(hub_30d[1] or 0)

    # ─── Usage (last 30d) ───────────────────────────────────────
    tokens_30d = int(
        await db.scalar(
            select(func.coalesce(func.sum(UsageEvent.total_tokens), 0)).where(
                UsageEvent.event_type == EVENT_LLM_CALL,
                UsageEvent.created_at >= month_ago,
            )
        )
        or 0
    )
    kb_queries_30d = int(
        await db.scalar(
            select(func.count())
            .select_from(UsageEvent)
            .where(
                UsageEvent.event_type == EVENT_KB_QUERY,
                UsageEvent.created_at >= month_ago,
            )
        )
        or 0
    )

    # ─── Top orgs by token usage (30d) ──────────────────────────
    top_orgs_rows = (
        await db.execute(
            select(
                Organization.id,
                Organization.name,
                Organization.slug,
                Organization.plan,
                func.coalesce(func.sum(UsageEvent.total_tokens), 0).label("tokens"),
            )
            .select_from(Organization)
            .join(Workspace, Workspace.organization_id == Organization.id)
            .join(UsageEvent, UsageEvent.workspace_id == Workspace.id)
            .where(
                UsageEvent.event_type == EVENT_LLM_CALL,
                UsageEvent.created_at >= month_ago,
            )
            .group_by(Organization.id)
            .order_by(func.coalesce(func.sum(UsageEvent.total_tokens), 0).desc())
            .limit(10)
        )
    ).all()
    top_orgs = [
        {
            "id": str(r.id),
            "name": r.name,
            "slug": r.slug,
            "plan": r.plan,
            "tokens": int(r.tokens or 0),
        }
        for r in top_orgs_rows
    ]

    # ─── Resource counts (depth proxies) ────────────────────────
    workspaces_total = int(await db.scalar(select(func.count()).select_from(Workspace)) or 0)
    agents_total = int(await db.scalar(select(func.count()).select_from(Agent)) or 0)
    convos_30d = int(
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.created_at >= month_ago)
        )
        or 0
    )

    return {
        "as_of": now.isoformat(),
        "orgs": {
            "total": orgs_total,
            "new_30d": orgs_new_30d,
            "new_7d": orgs_new_7d,
            "by_plan": by_plan,
        },
        "users": {
            "total": users_total,
            "active_30d": users_active_30d,
            "active_7d": users_active_7d,
            "activity_rate_pct": round(activity_rate, 1),
        },
        "subscriptions": {
            "live": live_subs,
            "cancel_scheduled": cancel_scheduled,
        },
        "revenue": {
            "mrr_usd_cents": mrr_usd_cents,
            "hub_total_cents": hub_revenue_cents,
            "hub_total_purchases": hub_purchases_total,
            "hub_30d_cents": hub_revenue_30d_cents,
            "hub_30d_purchases": hub_purchases_30d,
        },
        "usage_30d": {
            "tokens": tokens_30d,
            "kb_queries": kb_queries_30d,
            "conversations": convos_30d,
        },
        "resources": {
            "workspaces": workspaces_total,
            "agents": agents_total,
        },
        "top_orgs_by_tokens_30d": top_orgs,
        # Contracts module isn't built yet — keep the shape so the FE
        # tile renders with a "Coming soon" placeholder. When the
        # ``org_contracts`` table lands, populate from there.
        "contracts": {
            "available": False,
            "signed": 0,
            "active": 0,
            "expiring_30d": 0,
            "total_value_cents": 0,
        },
    }
