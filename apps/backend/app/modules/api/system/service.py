"""System (root) org service — operations the platform owner performs
across all customer orgs. All callers MUST be system-org admins
(enforced at router level via :func:`require_platform_admin`).
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.organization_member import (
    ORG_ROLE_OWNER,
    OrganizationMember,
)
from app.models.user import User
from app.models.workspace import Workspace
from app.modules.api.system.schemas import SystemOrgDetail, SystemOrgRow


class SystemOrgError(ValueError):
    """Service-level errors — router maps to 400/404/409."""


# ─── Reads ─────────────────────────────────────────────────────────


async def list_orgs(
    db: AsyncSession,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SystemOrgRow], int]:
    """Paginated org list with member + workspace counters.

    Returns (rows, total). Counter subqueries are cheap because both
    bridge tables are indexed on ``organization_id``.
    """
    member_count = (
        select(func.count())
        .select_from(OrganizationMember)
        .where(OrganizationMember.organization_id == Organization.id)
        .correlate(Organization)
        .scalar_subquery()
    )
    workspace_count = (
        select(func.count())
        .select_from(Workspace)
        .where(Workspace.organization_id == Organization.id)
        .correlate(Organization)
        .scalar_subquery()
    )

    stmt = select(
        Organization,
        member_count.label("member_count"),
        workspace_count.label("workspace_count"),
    )
    count_stmt = select(func.count()).select_from(Organization)

    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            (func.lower(Organization.name).like(like))
            | (func.lower(Organization.slug).like(like))
        )
        count_stmt = count_stmt.where(
            (func.lower(Organization.name).like(like))
            | (func.lower(Organization.slug).like(like))
        )

    stmt = stmt.order_by(Organization.created_at.desc()).limit(limit).offset(offset)
    total = int(await db.scalar(count_stmt) or 0)

    rows = (await db.execute(stmt)).all()
    return [
        SystemOrgRow(
            id=org.id,
            name=org.name,
            slug=org.slug,
            plan=org.plan,
            billing_email=org.billing_email,
            is_system=org.is_system,
            member_count=int(mc or 0),
            workspace_count=int(wc or 0),
            created_at=org.created_at,
        )
        for org, mc, wc in rows
    ], total


async def get_org(db: AsyncSession, org_id: uuid.UUID) -> SystemOrgDetail | None:
    org = await db.get(Organization, org_id)
    if org is None:
        return None

    member_count = int(
        await db.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .where(OrganizationMember.organization_id == org_id)
        )
        or 0
    )
    workspace_count = int(
        await db.scalar(
            select(func.count())
            .select_from(Workspace)
            .where(Workspace.organization_id == org_id)
        )
        or 0
    )

    owner_email = await db.scalar(
        select(User.email)
        .join(
            OrganizationMember,
            OrganizationMember.user_id == User.id,
        )
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.role == ORG_ROLE_OWNER,
        )
        .order_by(OrganizationMember.joined_at)
        .limit(1)
    )

    return SystemOrgDetail(
        id=org.id,
        name=org.name,
        slug=org.slug,
        plan=org.plan,
        billing_email=org.billing_email,
        is_system=(org.slug == SYSTEM_ORG_SLUG),
        member_count=member_count,
        workspace_count=workspace_count,
        created_at=org.created_at,
        settings=org.settings or {},
        owner_email=owner_email,
    )


# ─── Writes ────────────────────────────────────────────────────────


async def create_org(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    owner_email: str,
    billing_email: str | None,
    plan: str | None,
) -> Organization:
    """Mint an org on behalf of a customer. Owner must already exist
    (V1 — we don't send signup invites from here)."""
    # Reserve the well-known slug so the customer-facing "create org"
    # path can't shadow the platform owner's slug, even before its row
    # exists. is_system stays the auth check; this is UX hygiene.
    from app.models.organization import SYSTEM_ORG_SLUG

    if slug == SYSTEM_ORG_SLUG:
        raise SystemOrgError("slug_reserved")

    owner = await db.scalar(select(User).where(User.email == owner_email.lower()))
    if owner is None:
        raise SystemOrgError("owner_not_found")

    org = Organization(
        name=name,
        slug=slug,
        billing_email=billing_email,
        plan=plan or "free",
    )
    db.add(org)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise SystemOrgError("slug_taken") from exc

    db.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=owner.id,
            role=ORG_ROLE_OWNER,
        )
    )
    await db.flush()
    return org


async def update_org(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    name: str | None,
    plan: str | None,
    billing_email: str | None,
    settings: dict | None,
) -> Organization | None:
    org = await db.get(Organization, org_id)
    if org is None:
        return None
    if name is not None:
        org.name = name
    if plan is not None:
        org.plan = plan
    if billing_email is not None:
        org.billing_email = billing_email
    if settings is not None:
        org.settings = settings
    await db.flush()
    return org


async def delete_org(db: AsyncSession, org_id: uuid.UUID) -> bool:
    """Hard-delete an org + its workspaces (FK CASCADE). Refuses to
    delete the system org — that would brick the admin surface."""
    org = await db.get(Organization, org_id)
    if org is None:
        return False
    if org.is_system:
        raise SystemOrgError("cannot_delete_system_org")
    await db.delete(org)
    await db.flush()
    return True
