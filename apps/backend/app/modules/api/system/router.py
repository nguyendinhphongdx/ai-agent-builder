"""``/api/system/*`` — platform admin surface gated on system-org
membership. See :mod:`app.modules.api.system` for the rationale.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.api.system import packages_service, service, subs_service
from app.modules.api.system.schemas import (
    SystemOrgCreate,
    SystemOrgDetail,
    SystemOrgPatch,
    SystemPackageRow,
    SystemSubscriptionCancel,
    SystemSubscriptionRow,
    SystemSubscriptionSetPlan,
    SystemSubscriptionStats,
)
from app.modules.identity.auth.permissions import require_platform_admin
from app.platform.db.session import get_db

# Router-level dep — every endpoint below requires system-org admin.
router = APIRouter(
    prefix="/system",
    tags=["system"],
    dependencies=[Depends(require_platform_admin())],
)


# ─── Organizations ────────────────────────────────────────────────


@router.get("/organizations")
async def list_orgs_endpoint(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Paginated list of every org on the platform. Supports a simple
    ``search`` substring match against name + slug. Returns
    ``{rows, total}`` so the FE can render a count."""
    rows, total = await service.list_orgs(
        db, search=search, limit=limit, offset=offset
    )
    return {"rows": [r.model_dump() for r in rows], "total": total}


@router.get("/organizations/{org_id}", response_model=SystemOrgDetail)
async def get_org_endpoint(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    org = await service.get_org(db, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="org_not_found")
    return org


@router.post("/organizations", status_code=status.HTTP_201_CREATED)
async def create_org_endpoint(
    body: SystemOrgCreate,
    db: AsyncSession = Depends(get_db),
):
    """Mint an org for a customer. Owner email must resolve to an
    existing user. Returns the same payload shape as the detail
    endpoint so the FE can navigate straight to it."""
    try:
        org = await service.create_org(
            db,
            name=body.name,
            slug=body.slug,
            owner_email=body.owner_email,
            billing_email=body.billing_email,
            plan=body.plan,
        )
    except service.SystemOrgError as exc:
        # Map service codes to HTTP status the FE can branch on.
        code = str(exc)
        status_code = {
            "slug_taken": 409,
            "slug_reserved": 422,
            "owner_not_found": 404,
        }.get(code, 400)
        raise HTTPException(status_code=status_code, detail=code) from exc
    await db.commit()
    detail = await service.get_org(db, org.id)
    return detail


@router.patch("/organizations/{org_id}", response_model=SystemOrgDetail)
async def update_org_endpoint(
    org_id: uuid.UUID,
    body: SystemOrgPatch,
    db: AsyncSession = Depends(get_db),
):
    org = await service.update_org(
        db,
        org_id,
        name=body.name,
        plan=body.plan,
        billing_email=body.billing_email,
        settings=body.settings,
    )
    if org is None:
        raise HTTPException(status_code=404, detail="org_not_found")
    await db.commit()
    detail = await service.get_org(db, org_id)
    assert detail is not None  # just fetched above
    return detail


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org_endpoint(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    try:
        ok = await service.delete_org(db, org_id)
    except service.SystemOrgError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="org_not_found")
    await db.commit()
    return None


# ─── Subscriptions ────────────────────────────────────────────────


@router.get("/subscriptions")
async def list_subscriptions_endpoint(
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    plan: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """All orgs with their (optional) subscription row, joined for one-shot display.

    ``status=none`` filters to orgs that never had a sub (implicit free).
    """
    rows, total = await subs_service.list_subscriptions(
        db, status=status_filter, plan=plan, limit=limit, offset=offset
    )
    return {"rows": [r.model_dump() for r in rows], "total": total}


@router.get("/subscriptions/stats", response_model=SystemSubscriptionStats)
async def subscriptions_stats_endpoint(db: AsyncSession = Depends(get_db)):
    """Aggregate counters for the admin header tile."""
    return await subs_service.aggregate(db)


@router.get("/subscriptions/{org_id}", response_model=SystemSubscriptionRow)
async def get_subscription_endpoint(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    row = await subs_service.get_subscription_detail(db, org_id)
    if row is None:
        raise HTTPException(status_code=404, detail="org_not_found")
    return row


@router.post("/subscriptions/{org_id}/set-plan", response_model=SystemSubscriptionRow)
async def set_plan_endpoint(
    org_id: uuid.UUID,
    body: SystemSubscriptionSetPlan,
    db: AsyncSession = Depends(get_db),
):
    """Comp an org onto a plan without Stripe — used for trials,
    enterprise deals signed offline, internal staff orgs, etc."""
    await subs_service.set_plan(db, org_id, body.plan_code)
    await db.commit()
    row = await subs_service.get_subscription_detail(db, org_id)
    assert row is not None
    return row


@router.post("/subscriptions/{org_id}/cancel", response_model=SystemSubscriptionRow)
async def cancel_subscription_endpoint(
    org_id: uuid.UUID,
    body: SystemSubscriptionCancel,
    db: AsyncSession = Depends(get_db),
):
    sub = await subs_service.cancel(db, org_id, immediate=body.immediate)
    if sub is None:
        raise HTTPException(status_code=404, detail="subscription_not_found")
    await db.commit()
    row = await subs_service.get_subscription_detail(db, org_id)
    assert row is not None
    return row


# ─── Packages (read-only) ─────────────────────────────────────────


@router.get("/packages", response_model=list[SystemPackageRow])
async def list_packages_endpoint(db: AsyncSession = Depends(get_db)):
    """Plan catalogue with live active-org counts per tier. Read-only
    — to change a plan, edit ``plans.py`` and redeploy."""
    return await packages_service.list_packages(db)
