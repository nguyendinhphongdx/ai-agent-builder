"""Phase 2.3 Block 5 — quota guards.

Pure unit-ish test: synthetic usage_events rows + free-plan org →
``enforce_tokens`` raises 402 once we cross the cap.
"""
from __future__ import annotations

import pytest

from app.billing.plans import PLAN_FREE, PLAN_PRO, PLANS
from app.billing.quota import (
    QuotaExceeded,
    enforce_kb_queries,
    enforce_tokens,
    get_quota_state,
)
from app.context import reset_current_workspace_id, set_current_workspace_id
from app.models.organization import Organization
from app.models.usage_event import EVENT_KB_QUERY, EVENT_LLM_CALL, UsageEvent
from app.models.workspace import Workspace
from tests.factories import UserFactory, create


async def _make_org_workspace(db, plan: str = PLAN_FREE) -> tuple[Organization, Workspace]:
    user = await create(db, UserFactory)
    org = Organization(
        name="Acme",
        slug=f"acme-{user.id.hex[:6]}",
        plan=plan,
    )
    db.add(org)
    await db.flush()
    ws = Workspace(
        organization_id=org.id,
        name="Default",
        slug="default",
        is_personal=False,
    )
    db.add(ws)
    await db.flush()
    return org, ws


async def _add_tokens(db, ws_id, total: int) -> None:
    """Seed one big usage_events row representing ``total`` LLM tokens."""
    db.add(
        UsageEvent(
            workspace_id=ws_id,
            event_type=EVENT_LLM_CALL,
            total_tokens=total,
            prompt_tokens=total // 2,
            completion_tokens=total - total // 2,
        )
    )
    await db.flush()


async def _add_kb_queries(db, ws_id, count: int) -> None:
    for _ in range(count):
        db.add(UsageEvent(workspace_id=ws_id, event_type=EVENT_KB_QUERY))
    await db.flush()


async def test_get_quota_state_under_limit(db_session) -> None:
    _, ws = await _make_org_workspace(db_session, plan=PLAN_FREE)
    await _add_tokens(db_session, ws.id, 50_000)

    state = await get_quota_state(db_session, ws.id)
    assert state.plan.code == PLAN_FREE
    assert state.tokens_used == 50_000
    assert state.tokens_limit == PLANS[PLAN_FREE].monthly_llm_tokens
    assert not state.tokens_over


async def test_enforce_tokens_raises_when_over_free_plan(db_session) -> None:
    _, ws = await _make_org_workspace(db_session, plan=PLAN_FREE)
    # Free plan: 100k tokens. Seed 150k → over cap.
    await _add_tokens(db_session, ws.id, 150_000)

    token = set_current_workspace_id(ws.id)
    try:
        with pytest.raises(QuotaExceeded) as exc:
            await enforce_tokens(db_session)
        # 402 + structured detail so FE can render plan-aware prompt.
        assert exc.value.status_code == 402
        detail = exc.value.detail
        assert detail["kind"] == "tokens"
        assert detail["plan"] == PLAN_FREE
        assert detail["limit"] == PLANS[PLAN_FREE].monthly_llm_tokens
    finally:
        reset_current_workspace_id(token)


async def test_enforce_tokens_passthrough_on_pro_no_metered_set(db_session) -> None:
    """Pro tier has metered_price_setting set, but until env is
    populated the price-id resolves to None. Without a metered
    price the guard should still hard-block — even on paid tiers —
    because there's no Stripe overage line item to ship to.
    """
    _, ws = await _make_org_workspace(db_session, plan=PLAN_PRO)
    # Pro plan: 10M tokens. Seed 11M → over cap. No metered price
    # env var set in tests → has_overage_pricing False → block.
    await _add_tokens(db_session, ws.id, 11_000_000)

    token = set_current_workspace_id(ws.id)
    try:
        with pytest.raises(QuotaExceeded) as exc:
            await enforce_tokens(db_session)
        assert exc.value.detail["plan"] == PLAN_PRO
    finally:
        reset_current_workspace_id(token)


async def test_enforce_kb_queries_separate_counter(db_session) -> None:
    """KB quota uses event count, not token sum — exhausting tokens
    doesn't touch KB queries and vice versa."""
    _, ws = await _make_org_workspace(db_session, plan=PLAN_FREE)
    # Free plan: 1k KB queries. Seed 1k + 5 = over.
    await _add_kb_queries(db_session, ws.id, 1005)

    token = set_current_workspace_id(ws.id)
    try:
        with pytest.raises(QuotaExceeded) as exc:
            await enforce_kb_queries(db_session)
        assert exc.value.detail["kind"] == "kb_queries"
    finally:
        reset_current_workspace_id(token)
