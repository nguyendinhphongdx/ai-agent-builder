"""Billing service — subscription state + effective plan resolution.

Reads:
  - effective_plan_for_org(org_id) → Plan
    Single canonical resolver everything else should call. Reads
    OrgSubscription first; falls back to organizations.plan; falls
    back to free.
  - get_subscription(org_id) → OrgSubscription | None
  - active_workspace_plan(db) → Plan
    Convenience: resolves via the ContextVar-set workspace.

Writes (used by webhook handlers + checkout flow):
  - upsert_subscription_from_stripe(...) — webhook adapter
  - set_plan(org_id, plan_code) — admin / test fallback

Stripe operations live in ``app/billing/stripe_client.py`` (Block 2).
This module never imports stripe so quota lookups stay zero-cost.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import PLAN_FREE, Plan, get_plan
from app.context import current_workspace_id_or_none
from app.models.org_subscription import LIVE_STATUSES, OrgSubscription
from app.models.organization import Organization
from app.models.workspace import Workspace


async def get_subscription(
    db: AsyncSession, organization_id: uuid.UUID
) -> OrgSubscription | None:
    return await db.scalar(
        select(OrgSubscription).where(
            OrgSubscription.organization_id == organization_id
        )
    )


async def effective_plan_for_org(
    db: AsyncSession, organization_id: uuid.UUID
) -> Plan:
    """Resolve the plan currently applied to an organization.

    Live subscription wins. ``organizations.plan`` is the legacy
    pointer; we keep it in sync via webhook handlers but read the
    subscription row first so a stale ``plan`` column never
    over-grants entitlements.
    """
    sub = await get_subscription(db, organization_id)
    if sub is not None and sub.status in LIVE_STATUSES:
        return get_plan(sub.plan_code)
    org = await db.get(Organization, organization_id)
    return get_plan(org.plan if org else None)


async def active_workspace_plan(db: AsyncSession) -> Plan:
    """Convenience for request-scoped callers — read the workspace
    from the ContextVar and resolve its org's plan.

    Returns free if no workspace is bound to the request (e.g. an
    admin-tooling endpoint that runs outside any tenant).
    """
    workspace_id = current_workspace_id_or_none()
    if workspace_id is None:
        return get_plan(PLAN_FREE)
    org_id = await db.scalar(
        select(Workspace.organization_id).where(Workspace.id == workspace_id)
    )
    if org_id is None:
        return get_plan(PLAN_FREE)
    return await effective_plan_for_org(db, org_id)


async def upsert_subscription_from_stripe(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    plan_code: str,
    status: str,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
    stripe_metered_item_id: str | None = None,
    current_period_start: datetime | None = None,
    current_period_end: datetime | None = None,
    cancel_at_period_end: bool = False,
) -> OrgSubscription:
    """Adapter for webhook handlers — idempotent upsert by org id.

    Also mirrors ``plan_code`` onto ``organizations.plan`` so legacy
    feature checks that still read the org column stay accurate.
    """
    sub = await get_subscription(db, organization_id)
    if sub is None:
        sub = OrgSubscription(
            organization_id=organization_id,
            plan_code=plan_code,
            status=status,
        )
        db.add(sub)
    sub.plan_code = plan_code
    sub.status = status
    if stripe_customer_id is not None:
        sub.stripe_customer_id = stripe_customer_id
    if stripe_subscription_id is not None:
        sub.stripe_subscription_id = stripe_subscription_id
    if stripe_metered_item_id is not None:
        sub.stripe_metered_item_id = stripe_metered_item_id
    if current_period_start is not None:
        sub.current_period_start = current_period_start
    if current_period_end is not None:
        sub.current_period_end = current_period_end
    sub.cancel_at_period_end = cancel_at_period_end

    # Mirror to the org row for the cheap-read path.
    org = await db.get(Organization, organization_id)
    if org is not None:
        org.plan = plan_code

    await db.flush()
    return sub


async def set_plan(
    db: AsyncSession, organization_id: uuid.UUID, plan_code: str
) -> OrgSubscription:
    """Admin / test backdoor — set plan without going through Stripe.

    Useful for: comping an enterprise customer pre-Stripe-deal,
    bumping a beta tester to pro, integration tests that need a
    specific tier without mocking the full webhook flow.
    """
    return await upsert_subscription_from_stripe(
        db,
        organization_id=organization_id,
        plan_code=plan_code,
        status="active",
        stripe_customer_id=None,
        stripe_subscription_id=None,
    )
