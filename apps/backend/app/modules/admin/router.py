"""Admin HTTP endpoints. Min-role gate per endpoint.

Hierarchy: user < moderator < support < admin
- moderator: hub moderation (feature, suspend templates) + view stats
- support:   inherits moderator + ban users + refund purchases
- admin:     inherits everything + grant roles
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.admin import service
from app.modules.admin.jobs import router as admin_jobs_router
from app.modules.admin.schemas import (
    AdminActionRow,
    AdminPurchaseRow,
    AdminStats,
    AdminTemplateRow,
    AdminUserRow,
    GrantRoleRequest,
    PayoutSuspendRequest,
    RefundRequest,
    SettlePurchaseRequest,
    TemplateModerationRequest,
    UserBanRequest,
)
from app.modules.audit.router import admin_router as admin_audit_router
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.permissions import UserRole, require_role
from app.platform.db.session import get_db

# Auth + moderator gate at router level — every admin endpoint needs at
# least moderator. Endpoints that need higher (support/admin) declare an
# extra dep individually.
router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[
        Depends(get_current_user),
        Depends(require_role(UserRole.MODERATOR)),
    ],
)

# Jobs DLQ inspector — inherits the moderator+ gate from the parent.
router.include_router(admin_jobs_router)

# Audit log query surface — same gate.
router.include_router(admin_audit_router)


# ─── Templates (moderator+) ───────────────────────────────────────────


@router.get("/templates", response_model=list[AdminTemplateRow])
async def list_templates_endpoint(
    status: str | None = Query(None, pattern="^(draft|published|suspended|archived)$"),
    q: str | None = Query(None, description="Search title (ILIKE)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_all_templates(
        db, status=status, query=q, limit=limit, offset=offset
    )
    return [
        AdminTemplateRow(
            id=t.id,
            slug=t.slug,
            title=t.title,
            author_user_id=t.user_id,
            author_email=email,
            author_name=t.author_name,
            status=t.status,
            is_featured=t.is_featured,
            price_cents=t.price_cents,
            fork_count=t.fork_count,
            rating_avg=t.rating_avg,
            rating_count=t.rating_count,
            created_at=t.created_at,
            published_at=t.published_at,
        )
        for t, email in rows
    ]


@router.patch("/templates/{template_id}", response_model=AdminTemplateRow)
async def moderate_template_endpoint(
    template_id: uuid.UUID,
    body: TemplateModerationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set is_featured and/or change status (suspend/archive/republish)."""
    try:
        template = await service.moderate_template(
            db,
            template_id,
            is_featured=body.is_featured,
            status=body.status,
            reason=body.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await db.commit()
    return AdminTemplateRow(
        id=template.id,
        slug=template.slug,
        title=template.title,
        author_user_id=template.user_id,
        author_email=None,  # no email on this path; UI re-fetches list
        author_name=template.author_name,
        status=template.status,
        is_featured=template.is_featured,
        price_cents=template.price_cents,
        fork_count=template.fork_count,
        rating_avg=template.rating_avg,
        rating_count=template.rating_count,
        created_at=template.created_at,
        published_at=template.published_at,
    )


# ─── Users (support+) ─────────────────────────────────────────────────


@router.get(
    "/users",
    response_model=list[AdminUserRow],
    dependencies=[Depends(require_role(UserRole.SUPPORT))],
)
async def list_users_endpoint(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    users = await service.list_users(db, query=q, limit=limit, offset=offset)
    return [AdminUserRow.model_validate(u, from_attributes=True) for u in users]


@router.patch(
    "/users/{user_id}/ban",
    response_model=AdminUserRow,
    dependencies=[Depends(require_role(UserRole.SUPPORT))],
)
async def ban_user_endpoint(
    user_id: uuid.UUID,
    body: UserBanRequest,
    db: AsyncSession = Depends(get_db),
):
    """Toggle is_active. Banning a user bumps token_version → forces logout."""
    try:
        user = await service.set_user_active(
            db, user_id, is_active=body.is_active, reason=body.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return AdminUserRow.model_validate(user, from_attributes=True)


@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserRow,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def grant_role_endpoint(
    user_id: uuid.UUID,
    body: GrantRoleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Admin-only — grant or downgrade a platform role."""
    try:
        user = await service.grant_role(db, user_id, role=body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return AdminUserRow.model_validate(user, from_attributes=True)


@router.patch(
    "/users/{user_id}/payouts",
    response_model=AdminUserRow,
    dependencies=[Depends(require_role(UserRole.SUPPORT))],
)
async def set_payout_status_endpoint(
    user_id: uuid.UUID,
    body: PayoutSuspendRequest,
    db: AsyncSession = Depends(get_db),
):
    """Suspend or restore an author's payout state. Support+ only.

    Flips both Stripe Connect flags on the User row. Authors with
    `enabled=False` can't publish paid templates and existing paid
    checkouts on their templates start failing the
    `can_receive_payouts` gate.
    """
    try:
        user = await service.set_user_payout_status(
            db, user_id, enabled=body.enabled, reason=body.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return AdminUserRow.model_validate(user, from_attributes=True)


# ─── Purchases (support+) ─────────────────────────────────────────────


@router.get(
    "/purchases",
    response_model=list[AdminPurchaseRow],
    dependencies=[Depends(require_role(UserRole.SUPPORT))],
)
async def list_purchases_endpoint(
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_purchases(
        db, status=status, limit=limit, offset=offset
    )
    return [
        AdminPurchaseRow(
            id=p.id,
            buyer_user_id=p.buyer_id,
            buyer_email=email,
            template_id=p.template_id,
            template_title=title,
            price_paid_cents=p.price_paid_cents,
            currency=p.currency,
            status=p.status,
            provider=p.provider,
            provider_transaction_id=p.provider_transaction_id,
            purchased_at=p.purchased_at,
            refunded_at=p.refunded_at,
            settled_at=p.settled_at,
            settlement_reference=p.settlement_reference,
        )
        for p, email, title in rows
    ]


@router.post(
    "/purchases/{purchase_id}/refund",
    response_model=AdminPurchaseRow,
    dependencies=[Depends(require_role(UserRole.SUPPORT))],
)
async def refund_endpoint(
    purchase_id: uuid.UUID,
    body: RefundRequest,
    db: AsyncSession = Depends(get_db),
):
    """Issue a Stripe refund and mark the purchase refunded."""
    try:
        purchase = await service.refund_purchase(
            db, purchase_id, reason=body.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    await db.commit()
    return _purchase_row(purchase)


@router.post(
    "/purchases/{purchase_id}/settle",
    response_model=AdminPurchaseRow,
    dependencies=[Depends(require_role(UserRole.SUPPORT))],
)
async def settle_endpoint(
    purchase_id: uuid.UUID,
    body: SettlePurchaseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a paid purchase as settled — i.e. the platform has paid the
    author for it (Stripe transfer-id, MoMo bank transfer, etc.).

    Idempotent: re-marking is a no-op except the audit log entry.
    """
    try:
        purchase = await service.mark_purchase_settled(
            db, purchase_id, reference=body.reference
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return _purchase_row(purchase)


def _purchase_row(p) -> AdminPurchaseRow:
    """Build the response row from a Purchase ORM object — mirror of the
    list-endpoint shape for the single-row write endpoints. Buyer email +
    template title aren't joined here because the write endpoints don't
    need them; consumers refetch the list after a write."""
    return AdminPurchaseRow(
        id=p.id,
        buyer_user_id=p.buyer_id,
        buyer_email=None,
        template_id=p.template_id,
        template_title=None,
        price_paid_cents=p.price_paid_cents,
        currency=p.currency,
        status=p.status,
        provider=p.provider,
        provider_transaction_id=p.provider_transaction_id,
        purchased_at=p.purchased_at,
        refunded_at=p.refunded_at,
        settled_at=p.settled_at,
        settlement_reference=p.settlement_reference,
    )


# ─── Stats (moderator+) ───────────────────────────────────────────────


@router.get("/stats", response_model=AdminStats)
async def stats_endpoint(db: AsyncSession = Depends(get_db)):
    return AdminStats(**(await service.get_stats(db)))


# ─── Audit log (moderator+) ───────────────────────────────────────────


@router.get("/audit", response_model=list[AdminActionRow])
async def audit_endpoint(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    rows = await service.list_admin_actions(db, limit=limit, offset=offset)
    return [
        AdminActionRow(
            id=a.id,
            actor_user_id=a.actor_user_id,
            actor_email=email,
            action=a.action,
            target_type=a.target_type,
            target_id=a.target_id,
            details=a.details or {},
            created_at=a.created_at,
        )
        for a, email in rows
    ]
