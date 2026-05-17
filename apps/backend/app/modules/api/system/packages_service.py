"""Read-only serializer over the in-code PLANS catalogue.

PLANS is declarative (see ``plans.py``) — changing tiers is a code
deploy, not an admin form. This module just surfaces the catalogue
through the admin API and enriches each row with the live count of
orgs currently resolved to that plan.
"""
from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.org_subscription import LIVE_STATUSES, OrgSubscription
from app.models.organization import Organization
from app.modules.api.system.schemas import SystemPackageRow
from app.modules.commerce.payments.subscriptions.plans import PLANS


async def list_packages(db: AsyncSession) -> list[SystemPackageRow]:
    """All PLANS, sorted by their declaration order, with active-org counts.

    "Effective plan" mirrors ``billing.effective_plan_for_org``: live
    subscription wins, else fall back to ``organizations.plan``. Done
    in one SQL pass with COALESCE so the count is consistent with what
    quota guards see.
    """
    # Effective plan code per org = sub.plan_code IF live, else org.plan.
    # Postgres needs the full expression (not the alias) in GROUP BY.
    effective_plan = case(
        (OrgSubscription.status.in_(LIVE_STATUSES), OrgSubscription.plan_code),
        else_=Organization.plan,
    )

    rows = (
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
    counts: dict[str, int] = {plan_code: int(count or 0) for plan_code, count in rows}

    return [
        SystemPackageRow(
            code=plan.code,
            name=plan.name,
            monthly_llm_tokens=plan.monthly_llm_tokens,
            monthly_kb_queries=plan.monthly_kb_queries,
            max_workspaces=plan.max_workspaces,
            max_members=plan.max_members,
            features=plan.features,
            stripe_price_id=plan.stripe_price_id(),
            stripe_metered_price_id=plan.stripe_metered_price_id(),
            is_self_serve=plan.is_self_serve(),
            active_orgs=counts.get(plan.code, 0),
        )
        for plan in PLANS.values()
    ]
