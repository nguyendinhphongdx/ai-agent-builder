"""Phase 2.3 Block 4 — webhook handlers update OrgSubscription correctly.

No Stripe HTTP — we feed the handlers raw event payloads matching
Stripe's documented shape and assert the resulting DB state.
"""
from __future__ import annotations

from app.modules.billing.plans import PLAN_FREE, PLAN_PRO, PLAN_STARTER
from app.modules.billing.webhooks import (
    handle_invoice_payment_failed,
    handle_subscription_deleted,
    handle_subscription_event,
)
from app.models.organization import Organization
from tests.factories import UserFactory, create


async def _make_org(db, slug_suffix: str) -> Organization:
    user = await create(db, UserFactory)
    org = Organization(
        name="Acme",
        slug=f"acme-{slug_suffix}-{user.id.hex[:6]}",
        plan="free",
    )
    db.add(org)
    await db.flush()
    return org


def _sub_obj(*, org_id, plan_code, status="active", sub_id="sub_1", **overrides):
    """Minimal customer.subscription event shape."""
    base = {
        "id": sub_id,
        "customer": "cus_1",
        "status": status,
        "current_period_start": 1700000000,
        "current_period_end": 1702000000,
        "cancel_at_period_end": False,
        "metadata": {
            "organization_id": str(org_id),
            "plan_code": plan_code,
        },
        "items": {
            "data": [
                {
                    "id": "si_base",
                    "price": {"recurring": {"usage_type": "licensed"}},
                },
                {
                    "id": "si_metered",
                    "price": {"recurring": {"usage_type": "metered"}},
                },
            ]
        },
    }
    base.update(overrides)
    return base


async def test_subscription_created_provisions_row(db_session) -> None:
    """customer.subscription.created → OrgSubscription row written,
    plan mirrored onto organizations.plan, metered item id captured."""
    org = await _make_org(db_session, "create")

    sub = await handle_subscription_event(
        db_session, _sub_obj(org_id=org.id, plan_code=PLAN_STARTER)
    )
    assert sub is not None
    assert sub.plan_code == PLAN_STARTER
    assert sub.status == "active"
    assert sub.stripe_customer_id == "cus_1"
    assert sub.stripe_subscription_id == "sub_1"
    # Block 4's _find_metered_item walks items[] and picks the
    # usage_type=metered one — the licensed line item is skipped.
    assert sub.stripe_metered_item_id == "si_metered"

    await db_session.refresh(org)
    assert org.plan == PLAN_STARTER


async def test_subscription_updated_is_upsert(db_session) -> None:
    """Same event delivered twice doesn't duplicate the row, and a
    plan-code change reflects on the second delivery."""
    org = await _make_org(db_session, "update")

    await handle_subscription_event(
        db_session, _sub_obj(org_id=org.id, plan_code=PLAN_STARTER)
    )
    sub = await handle_subscription_event(
        db_session, _sub_obj(org_id=org.id, plan_code=PLAN_PRO)
    )
    assert sub.plan_code == PLAN_PRO

    await db_session.refresh(org)
    assert org.plan == PLAN_PRO


async def test_subscription_deleted_falls_back_to_free(db_session) -> None:
    """Final cancel event drops org.plan to free even though the
    subscription row keeps its last billed plan_code (for analytics)."""
    org = await _make_org(db_session, "delete")
    await handle_subscription_event(
        db_session, _sub_obj(org_id=org.id, plan_code=PLAN_PRO)
    )

    sub = await handle_subscription_deleted(
        db_session,
        _sub_obj(org_id=org.id, plan_code=PLAN_PRO, status="canceled"),
    )
    assert sub is not None
    assert sub.status == "canceled"
    # Row retains the last billed plan for revenue analytics.
    assert sub.plan_code == PLAN_PRO

    await db_session.refresh(org)
    assert org.plan == PLAN_FREE


async def test_invoice_payment_failed_marks_past_due(db_session) -> None:
    org = await _make_org(db_session, "payfail")
    await handle_subscription_event(
        db_session, _sub_obj(org_id=org.id, plan_code=PLAN_PRO)
    )

    sub = await handle_invoice_payment_failed(
        db_session, {"subscription": "sub_1"}
    )
    assert sub is not None
    assert sub.status == "past_due"
    # Org plan stays on the billed tier during the grace window.
    await db_session.refresh(org)
    assert org.plan == PLAN_PRO
