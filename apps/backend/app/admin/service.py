"""Admin operations + audit log helper."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import current_user_id
from app.models.admin_action import AdminAction
from app.models.agent_template import AgentTemplate
from app.models.agent_template_purchase import AgentTemplatePurchase
from app.models.user import User

logger = logging.getLogger("agentforge")


# ─── Audit log ────────────────────────────────────────────────────────


async def log_admin_action(
    db: AsyncSession,
    *,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Append a row to admin_actions. Caller is responsible for committing.

    Reads the actor from request context (set by ``get_current_user``).
    """
    db.add(
        AdminAction(
            actor_user_id=current_user_id(),
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
        )
    )


# ─── Templates ────────────────────────────────────────────────────────


async def list_all_templates(
    db: AsyncSession,
    *,
    status: str | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[AgentTemplate, str | None]]:
    """All templates regardless of status, joined with author email."""
    stmt = (
        select(AgentTemplate, User.email)
        .join(User, AgentTemplate.user_id == User.id)
        .order_by(AgentTemplate.created_at.desc())
    )
    if status:
        stmt = stmt.where(AgentTemplate.status == status)
    if query:
        stmt = stmt.where(AgentTemplate.title.ilike(f"%{query}%"))

    result = await db.execute(stmt.limit(limit).offset(offset))
    return [(t, email) for t, email in result.all()]


async def moderate_template(
    db: AsyncSession,
    template_id: uuid.UUID,
    *,
    is_featured: bool | None,
    status: str | None,
    reason: str | None,
) -> AgentTemplate:
    """Set is_featured and/or status on a template (moderator+)."""
    template = await db.get(AgentTemplate, template_id)
    if template is None:
        raise ValueError("Template not found")

    changes: dict[str, Any] = {}
    if is_featured is not None and is_featured != template.is_featured:
        template.is_featured = is_featured
        changes["is_featured"] = is_featured
    if status is not None and status != template.status:
        template.status = status
        changes["status"] = status

    if changes:
        await log_admin_action(
            db,
            action="template.moderate",
            target_type="template",
            target_id=str(template_id),
            details={**changes, "reason": reason},
        )
        await db.flush()
        await db.refresh(template)

    return template


# ─── Users ────────────────────────────────────────────────────────────


async def list_users(
    db: AsyncSession, *, query: str | None = None, limit: int = 50, offset: int = 0
) -> list[User]:
    stmt = select(User).order_by(User.created_at.desc())
    if query:
        stmt = stmt.where(User.email.ilike(f"%{query}%"))
    result = await db.execute(stmt.limit(limit).offset(offset))
    return list(result.scalars().all())


async def set_user_active(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    is_active: bool,
    reason: str | None,
) -> User:
    """Ban (is_active=False) or unban a user. Bumps token_version on ban so
    existing JWTs stop working immediately."""
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")
    if user.id == current_user_id() and not is_active:
        raise ValueError("Cannot ban yourself")

    if user.is_active != is_active:
        user.is_active = is_active
        if not is_active:
            # Force-logout — see auth/dependencies token_version check.
            user.token_version = (user.token_version or 0) + 1

        await log_admin_action(
            db,
            action="user.ban" if not is_active else "user.unban",
            target_type="user",
            target_id=str(user_id),
            details={"reason": reason},
        )
        await db.flush()
        await db.refresh(user)

    return user


async def set_user_payout_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    enabled: bool,
    reason: str | None,
) -> User:
    """Override Stripe Connect payout flags on an author's User row.

    Used by moderation when an author is abusing the marketplace. We
    flip both ``stripe_charges_enabled`` and ``stripe_payouts_enabled``
    locally — Stripe's account stays as-is on their side, but our
    publish-paid + checkout gates start refusing because they read from
    our cached flags.

    Restoring (enabled=True) is rare; we usually wait for the author to
    re-onboard which fires a fresh ``account.updated`` webhook. Explicit
    re-enable is logged so it's auditable.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")

    changed = (
        user.stripe_charges_enabled != enabled
        or user.stripe_payouts_enabled != enabled
    )
    if changed:
        user.stripe_charges_enabled = enabled
        user.stripe_payouts_enabled = enabled
        await log_admin_action(
            db,
            action="user.suspend_payouts" if not enabled else "user.restore_payouts",
            target_type="user",
            target_id=str(user_id),
            details={"reason": reason},
        )
        await db.flush()
        await db.refresh(user)
    return user


async def grant_role(
    db: AsyncSession, user_id: uuid.UUID, *, role: str
) -> User:
    """Grant or downgrade a platform role. Admin-only."""
    user = await db.get(User, user_id)
    if user is None:
        raise ValueError("User not found")
    if user.id == current_user_id() and role != "admin":
        raise ValueError("Cannot revoke your own admin role")

    if user.role != role:
        previous = user.role
        user.role = role
        await log_admin_action(
            db,
            action="user.grant_role",
            target_type="user",
            target_id=str(user_id),
            details={"from": previous, "to": role},
        )
        await db.flush()
        await db.refresh(user)
    return user


# ─── Purchases ────────────────────────────────────────────────────────


async def list_purchases(
    db: AsyncSession,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[tuple[AgentTemplatePurchase, str | None, str | None]]:
    """Returns (purchase, buyer_email, template_title)."""
    stmt = (
        select(AgentTemplatePurchase, User.email, AgentTemplate.title)
        .join(User, AgentTemplatePurchase.buyer_id == User.id)
        .join(AgentTemplate, AgentTemplatePurchase.template_id == AgentTemplate.id)
        .order_by(AgentTemplatePurchase.purchased_at.desc())
    )
    if status:
        stmt = stmt.where(AgentTemplatePurchase.status == status)
    result = await db.execute(stmt.limit(limit).offset(offset))
    return [(p, email, title) for p, email, title in result.all()]


async def mark_purchase_settled(
    db: AsyncSession,
    purchase_id: uuid.UUID,
    *,
    reference: str | None,
) -> AgentTemplatePurchase:
    """Flip ``settled_at`` on a paid purchase. Idempotent — re-marking
    only refreshes the reference string + audit row.

    Stripe destination-charge rows can be auto-settled at payment time
    by the webhook (Stripe Connect handles the actual transfer). MoMo
    rows wait for ops to mark them after a manual bank transfer.
    """
    from datetime import datetime, timezone

    purchase = await db.get(AgentTemplatePurchase, purchase_id)
    if purchase is None:
        raise ValueError("Purchase not found")
    if purchase.status != "paid":
        raise ValueError(
            f"Purchase status is {purchase.status}, not paid — only paid purchases settle"
        )

    purchase.settled_at = purchase.settled_at or datetime.now(timezone.utc)
    if reference:
        purchase.settlement_reference = reference

    await log_admin_action(
        db,
        action="purchase.settle",
        target_type="purchase",
        target_id=str(purchase_id),
        details={
            "reference": reference,
            "amount_cents": purchase.price_paid_cents,
            "currency": purchase.currency,
            "provider": purchase.provider,
        },
    )
    await db.flush()
    await db.refresh(purchase)
    return purchase


async def refund_purchase(
    db: AsyncSession,
    purchase_id: uuid.UUID,
    *,
    reason: str | None,
) -> AgentTemplatePurchase:
    """Issue a refund via the originating provider and mark refunded.

    Dispatches by ``Purchase.provider`` (Stripe / MoMo). Free purchases
    (price=0) skip the gateway call — just flip status. Caller decides
    whether to commit.

    Raises:
        ValueError — purchase missing / not in 'paid' state
        RuntimeError — gateway refund failed (caller can retry)
    """
    purchase = await db.get(AgentTemplatePurchase, purchase_id)
    if purchase is None:
        raise ValueError("Purchase not found")
    if purchase.status != "paid":
        raise ValueError(f"Purchase status is {purchase.status}, not paid")

    if purchase.price_paid_cents > 0 and purchase.provider_transaction_id:
        # Real refund — delegate to the provider that issued the charge.
        from app.payments.providers import get_provider

        provider = get_provider(purchase.provider)
        await provider.refund(db, purchase, reason=reason)

    purchase.status = "refunded"
    purchase.refunded_at = datetime.now(timezone.utc)

    await log_admin_action(
        db,
        action="purchase.refund",
        target_type="purchase",
        target_id=str(purchase_id),
        details={
            "reason": reason,
            "amount_cents": purchase.price_paid_cents,
            "provider": purchase.provider,
        },
    )
    await db.flush()
    await db.refresh(purchase)
    return purchase


# ─── Stats ────────────────────────────────────────────────────────────


async def get_stats(db: AsyncSession) -> dict[str, Any]:
    """Cheap snapshot of platform counters. Run on demand from /admin/stats."""
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)

    total_users = await db.scalar(select(func.count(User.id))) or 0
    active_30d = await db.scalar(
        select(func.count(User.id)).where(User.last_login_at >= cutoff_30d)
    ) or 0
    total_templates = await db.scalar(select(func.count(AgentTemplate.id))) or 0
    published = await db.scalar(
        select(func.count(AgentTemplate.id)).where(AgentTemplate.status == "published")
    ) or 0
    total_forks = await db.scalar(
        select(func.coalesce(func.sum(AgentTemplate.fork_count), 0))
    ) or 0
    paid_purchases = await db.scalar(
        select(func.count(AgentTemplatePurchase.id)).where(
            AgentTemplatePurchase.status == "paid"
        )
    ) or 0
    revenue_30d = await db.scalar(
        select(func.coalesce(func.sum(AgentTemplatePurchase.price_paid_cents), 0)).where(
            AgentTemplatePurchase.status == "paid",
            AgentTemplatePurchase.purchased_at >= cutoff_30d,
        )
    ) or 0
    revenue_all = await db.scalar(
        select(func.coalesce(func.sum(AgentTemplatePurchase.price_paid_cents), 0)).where(
            AgentTemplatePurchase.status == "paid"
        )
    ) or 0

    return {
        "total_users": int(total_users),
        "active_users_30d": int(active_30d),
        "total_templates": int(total_templates),
        "published_templates": int(published),
        "total_forks": int(total_forks),
        "total_purchases_paid": int(paid_purchases),
        "revenue_cents_30d": int(revenue_30d),
        "revenue_cents_all_time": int(revenue_all),
    }


# ─── Audit log read ───────────────────────────────────────────────────


async def list_admin_actions(
    db: AsyncSession, *, limit: int = 100, offset: int = 0
) -> list[tuple[AdminAction, str | None]]:
    """Recent admin actions joined with actor email."""
    result = await db.execute(
        select(AdminAction, User.email)
        .outerjoin(User, AdminAction.actor_user_id == User.id)
        .order_by(desc(AdminAction.created_at))
        .limit(limit)
        .offset(offset)
    )
    return [(a, email) for a, email in result.all()]
