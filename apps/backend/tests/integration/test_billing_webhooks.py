"""Subscription provider webhook dispatch — OrgSubscription mutations.

No Stripe HTTP — we hand the verified-event dict to
``StripeSubscriptionProvider.process_event`` (the same entry point the
Hub Stripe receiver uses after signature verification) and assert the
resulting DB state.
"""
from __future__ import annotations

from typing import Any

from app.models.organization import Organization
from app.modules.commerce.payments.subscriptions.plans import (
    PLAN_FREE,
    PLAN_PRO,
    PLAN_STARTER,
)
from app.modules.commerce.payments.subscriptions.providers.stripe import (
    StripeSubscriptionProvider,
)
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
    """Minimal customer.subscription event-data object."""
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


def _event(event_type: str, obj: dict[str, Any]) -> dict[str, Any]:
    """Wrap an event-data object in the Stripe envelope."""
    return {"id": f"evt_{event_type}", "type": event_type, "data": {"object": obj}}


async def test_subscription_created_provisions_row(db_session) -> None:
    """customer.subscription.created → OrgSubscription row written,
    plan mirrored onto organizations.plan, metered item id captured."""
    org = await _make_org(db_session, "create")
    provider = StripeSubscriptionProvider()

    audit = await provider.process_event(
        db_session,
        event=_event(
            "customer.subscription.created",
            _sub_obj(org_id=org.id, plan_code=PLAN_STARTER),
        ),
    )
    assert audit["result"] == "subscription_upserted"

    # Re-read via the same path the dashboard uses.
    from app.modules.commerce.payments.subscriptions import service

    sub = await service.get_subscription(db_session, org.id)
    assert sub is not None
    assert sub.plan_code == PLAN_STARTER
    assert sub.status == "active"
    assert sub.stripe_customer_id == "cus_1"
    assert sub.stripe_subscription_id == "sub_1"
    # _find_metered_item walks items[] and picks the metered one.
    assert sub.stripe_metered_item_id == "si_metered"

    await db_session.refresh(org)
    assert org.plan == PLAN_STARTER


async def test_subscription_updated_is_upsert(db_session) -> None:
    """Re-delivery doesn't duplicate the row; a plan-code change
    reflects on the second delivery."""
    org = await _make_org(db_session, "update")
    provider = StripeSubscriptionProvider()

    await provider.process_event(
        db_session,
        event=_event(
            "customer.subscription.created",
            _sub_obj(org_id=org.id, plan_code=PLAN_STARTER),
        ),
    )
    await provider.process_event(
        db_session,
        event=_event(
            "customer.subscription.updated",
            _sub_obj(org_id=org.id, plan_code=PLAN_PRO),
        ),
    )

    from app.modules.commerce.payments.subscriptions import service

    sub = await service.get_subscription(db_session, org.id)
    assert sub is not None
    assert sub.plan_code == PLAN_PRO

    await db_session.refresh(org)
    assert org.plan == PLAN_PRO


async def test_subscription_deleted_falls_back_to_free(db_session) -> None:
    """Final cancel event drops org.plan to free even though the
    subscription row keeps its last billed plan_code (for analytics)."""
    org = await _make_org(db_session, "delete")
    provider = StripeSubscriptionProvider()

    await provider.process_event(
        db_session,
        event=_event(
            "customer.subscription.created",
            _sub_obj(org_id=org.id, plan_code=PLAN_PRO),
        ),
    )
    audit = await provider.process_event(
        db_session,
        event=_event(
            "customer.subscription.deleted",
            _sub_obj(org_id=org.id, plan_code=PLAN_PRO, status="canceled"),
        ),
    )
    assert audit["result"] == "subscription_canceled"

    from app.modules.commerce.payments.subscriptions import service

    sub = await service.get_subscription(db_session, org.id)
    assert sub is not None
    assert sub.status == "canceled"
    # Row retains the last billed plan for revenue analytics.
    assert sub.plan_code == PLAN_PRO

    await db_session.refresh(org)
    assert org.plan == PLAN_FREE


async def test_invoice_payment_failed_marks_past_due(db_session) -> None:
    org = await _make_org(db_session, "payfail")
    provider = StripeSubscriptionProvider()

    await provider.process_event(
        db_session,
        event=_event(
            "customer.subscription.created",
            _sub_obj(org_id=org.id, plan_code=PLAN_PRO),
        ),
    )
    audit = await provider.process_event(
        db_session,
        event=_event("invoice.payment_failed", {"subscription": "sub_1"}),
    )
    assert audit["result"] == "marked_past_due"

    from app.modules.commerce.payments.subscriptions import service

    sub = await service.get_subscription(db_session, org.id)
    assert sub is not None
    assert sub.status == "past_due"
    # Org plan stays on the billed tier during the grace window.
    await db_session.refresh(org)
    assert org.plan == PLAN_PRO


async def test_unrelated_event_is_ignored(db_session) -> None:
    """``checkout.session.completed`` belongs to the Hub flow, not us.
    Subscription provider sees it via the shared receiver only because
    of a bug — it should return ``ignored`` not mutate state."""
    provider = StripeSubscriptionProvider()
    audit = await provider.process_event(
        db_session, event=_event("checkout.session.completed", {})
    )
    assert audit["result"] == "ignored"
