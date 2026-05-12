"""Phase 2.3 Block 1 — plan resolution + subscription upsert.

Doesn't exercise Stripe (Block 2 wires that). Pure logic test of:
  - org_subscriptions row absent → effective plan = organizations.plan
  - row present + live status → row's plan_code wins
  - row present + canceled → falls back to organizations.plan
  - upsert mirrors plan_code onto organizations.plan
"""
from __future__ import annotations

from app.models.organization import Organization
from app.modules.commerce.payments.subscriptions import service as billing_service
from app.modules.commerce.payments.subscriptions.plans import (
    PLAN_FREE,
    PLAN_PRO,
    PLAN_STARTER,
)
from tests.factories import UserFactory, create


async def test_effective_plan_falls_back_to_org_column(db_session) -> None:
    """No subscription row → effective plan is whatever lives on the
    organizations.plan column (legacy or seed path)."""
    user = await create(db_session, UserFactory)
    org = Organization(name="Acme", slug=f"acme-{user.id.hex[:6]}", plan="pro")
    db_session.add(org)
    await db_session.flush()

    plan = await billing_service.effective_plan_for_org(db_session, org.id)
    assert plan.code == PLAN_PRO


async def test_effective_plan_subscription_wins(db_session) -> None:
    """Live subscription row overrides the org column — what Stripe
    says now is what's billable, not stale snapshot data."""
    user = await create(db_session, UserFactory)
    org = Organization(name="Acme", slug=f"acme-{user.id.hex[:6]}", plan="free")
    db_session.add(org)
    await db_session.flush()

    sub = await billing_service.upsert_subscription_from_stripe(
        db_session,
        organization_id=org.id,
        plan_code=PLAN_STARTER,
        status="active",
        stripe_customer_id="cus_x",
        stripe_subscription_id="sub_x",
    )
    assert sub.plan_code == PLAN_STARTER

    plan = await billing_service.effective_plan_for_org(db_session, org.id)
    assert plan.code == PLAN_STARTER

    # Mirror also happened on the org row — feature checks reading the
    # cheap column stay accurate without a join.
    await db_session.refresh(org)
    assert org.plan == PLAN_STARTER


async def test_effective_plan_canceled_subscription_falls_back(db_session) -> None:
    """Canceled status → not "live" → fall back to organizations.plan.

    This is the post-period-end downgrade path: webhook flips status
    to canceled, plan_code stays on what was billed, but quota guard
    should now read from the org column.
    """
    user = await create(db_session, UserFactory)
    org = Organization(name="Acme", slug=f"acme-{user.id.hex[:6]}", plan="free")
    db_session.add(org)
    await db_session.flush()

    sub = await billing_service.upsert_subscription_from_stripe(
        db_session,
        organization_id=org.id,
        plan_code=PLAN_PRO,
        status="canceled",
        stripe_customer_id="cus_x",
        stripe_subscription_id="sub_x",
    )
    assert sub.status == "canceled"

    # Webhook mirrors plan_code onto org.plan at write time — to
    # simulate the post-downgrade state we reset it back to free.
    org.plan = PLAN_FREE
    await db_session.flush()

    plan = await billing_service.effective_plan_for_org(db_session, org.id)
    assert plan.code == PLAN_FREE


async def test_set_plan_idempotent(db_session) -> None:
    """Admin backdoor — second call upserts, doesn't dup the row."""
    user = await create(db_session, UserFactory)
    org = Organization(name="Acme", slug=f"acme-{user.id.hex[:6]}", plan="free")
    db_session.add(org)
    await db_session.flush()

    sub1 = await billing_service.set_plan(db_session, org.id, PLAN_STARTER)
    sub2 = await billing_service.set_plan(db_session, org.id, PLAN_PRO)
    assert sub1.id == sub2.id
    assert sub2.plan_code == PLAN_PRO
