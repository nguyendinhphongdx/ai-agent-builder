"""Subscription queries + mutations for the system admin surface.

Reuses :mod:`app.modules.commerce.payments.subscriptions.service` for
the actual subscription state machine — this file is just the read +
fan-in layer the admin UI talks to.
"""
from __future__ import annotations

import uuid
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_subscription import LIVE_STATUSES, OrgSubscription
from app.models.organization import Organization
from app.modules.api.system.schemas import (
    SystemSubscriptionRow,
    SystemSubscriptionStats,
)
from app.modules.commerce.payments.subscriptions import service as billing


# ─── Reads ─────────────────────────────────────────────────────────


async def list_subscriptions(
    db: AsyncSession,
    *,
    status: str | None = None,
    plan: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[SystemSubscriptionRow], int]:
    """All orgs, with their subscription row (left-joined — orgs without
    a sub show as ``status='none'`` / ``plan_code='free'``).

    Returns (rows, total). Counting is cheap because the same WHERE
    applies to both subqueries.
    """
    stmt = (
        select(
            Organization.id,
            Organization.name,
            Organization.slug,
            Organization.plan,
            OrgSubscription.plan_code,
            OrgSubscription.status,
            OrgSubscription.current_period_end,
            OrgSubscription.cancel_at_period_end,
            OrgSubscription.stripe_subscription_id,
            OrgSubscription.created_at.label("sub_created_at"),
            Organization.created_at.label("org_created_at"),
        )
        .select_from(Organization)
        .outerjoin(
            OrgSubscription,
            OrgSubscription.organization_id == Organization.id,
        )
    )
    count_stmt = select(func.count()).select_from(Organization).outerjoin(
        OrgSubscription, OrgSubscription.organization_id == Organization.id
    )

    if status:
        if status == "none":
            stmt = stmt.where(OrgSubscription.id.is_(None))
            count_stmt = count_stmt.where(OrgSubscription.id.is_(None))
        else:
            stmt = stmt.where(OrgSubscription.status == status)
            count_stmt = count_stmt.where(OrgSubscription.status == status)
    if plan:
        stmt = stmt.where(
            func.coalesce(OrgSubscription.plan_code, Organization.plan) == plan
        )
        count_stmt = count_stmt.where(
            func.coalesce(OrgSubscription.plan_code, Organization.plan) == plan
        )

    stmt = stmt.order_by(Organization.created_at.desc()).limit(limit).offset(offset)
    total = int(await db.scalar(count_stmt) or 0)
    rows = (await db.execute(stmt)).all()

    return [
        SystemSubscriptionRow(
            org_id=r.id,
            org_name=r.name,
            org_slug=r.slug,
            # No sub row → fall back to the org.plan pointer (the legacy
            # 'free' default everyone gets at signup).
            plan_code=r.plan_code or r.plan,
            status=r.status or "none",
            is_live=(r.status in LIVE_STATUSES),
            current_period_end=r.current_period_end,
            cancel_at_period_end=bool(r.cancel_at_period_end),
            stripe_subscription_id=r.stripe_subscription_id,
            # Sub created_at when present, otherwise the org's own.
            created_at=r.sub_created_at or r.org_created_at,
        )
        for r in rows
    ], total


async def get_subscription_detail(
    db: AsyncSession, org_id: uuid.UUID
) -> SystemSubscriptionRow | None:
    rows, _ = await list_subscriptions(db, limit=1, offset=0)
    # list_subscriptions returns all orgs; filter to the one we want
    # via a fresh query — simpler than threading a filter through.
    org = await db.get(Organization, org_id)
    if org is None:
        return None
    sub = await billing.get_subscription(db, org_id)
    return SystemSubscriptionRow(
        org_id=org.id,
        org_name=org.name,
        org_slug=org.slug,
        plan_code=sub.plan_code if sub else org.plan,
        status=sub.status if sub else "none",
        is_live=bool(sub and sub.status in LIVE_STATUSES),
        current_period_end=sub.current_period_end if sub else None,
        cancel_at_period_end=bool(sub and sub.cancel_at_period_end),
        stripe_subscription_id=sub.stripe_subscription_id if sub else None,
        created_at=sub.created_at if sub else org.created_at,
    )


async def aggregate(db: AsyncSession) -> SystemSubscriptionStats:
    """Counter tile for the admin header — total orgs, by-status, by-plan."""
    total_orgs = int(await db.scalar(select(func.count()).select_from(Organization)) or 0)

    # Live subs split by status + plan in a single pass.
    rows = (
        await db.execute(
            select(
                OrgSubscription.status,
                OrgSubscription.plan_code,
                OrgSubscription.cancel_at_period_end,
            )
        )
    ).all()

    status_c: Counter[str] = Counter()
    plan_c: Counter[str] = Counter()
    cancel_scheduled = 0
    live = 0
    trialing = 0
    for status, plan_code, cancel in rows:
        status_c[status] += 1
        plan_c[plan_code] += 1
        if cancel:
            cancel_scheduled += 1
        if status in LIVE_STATUSES:
            live += 1
        if status == "trialing":
            trialing += 1

    # Orgs without a sub row are implicitly on the org.plan default;
    # surface those too so the by_plan total matches total_orgs.
    free_orgs = (
        await db.execute(
            select(Organization.plan, func.count())
            .outerjoin(
                OrgSubscription,
                OrgSubscription.organization_id == Organization.id,
            )
            .where(OrgSubscription.id.is_(None))
            .group_by(Organization.plan)
        )
    ).all()
    for plan_code, count in free_orgs:
        plan_c[plan_code] += int(count)

    return SystemSubscriptionStats(
        total_orgs=total_orgs,
        live_subs=live,
        by_status=dict(status_c),
        by_plan=dict(plan_c),
        trialing=trialing,
        cancel_scheduled=cancel_scheduled,
    )


# ─── Writes ────────────────────────────────────────────────────────


async def set_plan(
    db: AsyncSession, org_id: uuid.UUID, plan_code: str
) -> OrgSubscription:
    """Comp an org onto a plan without Stripe round-trip. Uses the
    billing service's existing backdoor so legacy quota checks via
    ``organizations.plan`` stay in sync."""
    return await billing.set_plan(db, org_id, plan_code)


async def cancel(
    db: AsyncSession, org_id: uuid.UUID, *, immediate: bool
) -> OrgSubscription | None:
    """Cancel a subscription. Default end-of-period so users keep
    access until the natural renewal date. ``immediate=true`` flips
    status to canceled now — use sparingly (fraud, ToS violation)."""
    sub = await billing.get_subscription(db, org_id)
    if sub is None:
        return None
    if immediate:
        sub.status = "canceled"
        sub.cancel_at_period_end = False
    else:
        sub.cancel_at_period_end = True
    await db.flush()
    return sub
