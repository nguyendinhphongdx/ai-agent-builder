"""Organizations service — CRUD + member ops.

Business invariants enforced here (router stays thin):
  * Slug uniqueness — surfaced as IntegrityError → 409.
  * Owner must exist. Demoting / removing the last owner of an org
    is rejected (``last_owner_protection``).
  * Inviting an email that doesn't resolve to an existing user
    returns ``user_not_found`` — email magic-link onboarding is
    a future feature.

Personal-org auto-creation is in
``app.modules.identity.workspaces.service.ensure_personal_workspace``
— this module is the surface for everything *after* signup.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import ORG_PLAN_FREE, Organization
from app.models.organization_member import (
    ORG_ROLE_OWNER,
    ORG_ROLES,
    OrganizationMember,
)
from app.models.user import User
from app.platform.context import current_user_id


class OrganizationServiceError(ValueError):
    """Catch-all for invariant violations. Router maps to 409/422."""


# ─── Reads ─────────────────────────────────────────────────────────


async def list_user_organizations(
    db: AsyncSession, user_id: uuid.UUID
) -> Sequence[tuple[Organization, str]]:
    """Every org the user is a member of, paired with their role.

    Returns rows in (org, role) tuple form so the router can render
    a single org-switcher payload without a second query.
    """
    rows = await db.execute(
        select(Organization, OrganizationMember.role)
        .join(
            OrganizationMember,
            OrganizationMember.organization_id == Organization.id,
        )
        .where(OrganizationMember.user_id == user_id)
        .order_by(Organization.created_at)
    )
    return [(org, role) for org, role in rows.all()]


async def get_organization(
    db: AsyncSession, organization_id: uuid.UUID
) -> Organization | None:
    return await db.scalar(
        select(Organization).where(Organization.id == organization_id)
    )


async def list_members(
    db: AsyncSession, organization_id: uuid.UUID
) -> Sequence[tuple[OrganizationMember, User]]:
    rows = await db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.joined_at)
    )
    return list(rows.all())


# ─── Writes ────────────────────────────────────────────────────────


async def create_organization(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    billing_email: str | None = None,
) -> Organization:
    """Create a fresh org with the caller as owner. Same flow whether
    invoked from the signup auto-create path or the
    ``POST /api/organizations`` endpoint."""
    user_id = current_user_id()
    org = Organization(
        name=name,
        slug=slug,
        billing_email=billing_email,
        plan=ORG_PLAN_FREE,
    )
    db.add(org)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise OrganizationServiceError("slug_taken") from exc

    db.add(
        OrganizationMember(
            organization_id=org.id,
            user_id=user_id,
            role=ORG_ROLE_OWNER,
        )
    )
    await db.flush()
    return org


async def update_organization(
    db: AsyncSession,
    org: Organization,
    *,
    name: str | None = None,
    billing_email: str | None = None,
    settings: dict | None = None,
) -> Organization:
    if name is not None:
        org.name = name
    if billing_email is not None:
        org.billing_email = billing_email
    if settings is not None:
        org.settings = settings
    await db.flush()
    return org


async def delete_organization(db: AsyncSession, org: Organization) -> None:
    """Hard-delete the org + every workspace inside it (FK CASCADE).
    Caller is responsible for confirming with the user; this just
    runs the DELETE."""
    await db.delete(org)
    await db.flush()


# ─── Members ───────────────────────────────────────────────────────


async def _resolve_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email.lower()))


async def _count_owners(
    db: AsyncSession, organization_id: uuid.UUID
) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(OrganizationMember)
        .where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == ORG_ROLE_OWNER,
        )
    )
    return int(count or 0)


async def invite_member(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    email: str,
    role: str,
) -> OrganizationMember:
    """Add an existing user to the org under ``role``.

    V1: the user must already exist (email lookup must hit). For
    cold-onboarding via magic link we'll wire a separate
    ``organization_invitations`` table later.
    """
    if role not in ORG_ROLES:
        raise OrganizationServiceError(f"invalid_role:{role}")
    user = await _resolve_user_by_email(db, email)
    if user is None:
        raise OrganizationServiceError("user_not_found")

    existing = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
        )
    )
    if existing is not None:
        raise OrganizationServiceError("already_member")

    member = OrganizationMember(
        organization_id=organization_id,
        user_id=user.id,
        role=role,
        invited_by=current_user_id(),
    )
    db.add(member)
    await db.flush()
    return member


async def update_member_role(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    role: str,
) -> OrganizationMember:
    if role not in ORG_ROLES:
        raise OrganizationServiceError(f"invalid_role:{role}")
    member = await db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    if member is None:
        raise OrganizationServiceError("not_a_member")

    # Last-owner protection — demoting the only owner leaves the org
    # unmanageable.
    if member.role == ORG_ROLE_OWNER and role != ORG_ROLE_OWNER:
        if await _count_owners(db, organization_id) <= 1:
            raise OrganizationServiceError("last_owner_protection")

    member.role = role
    await db.flush()
    return member


async def remove_member(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    member = await db.scalar(
        select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
    )
    if member is None:
        raise OrganizationServiceError("not_a_member")

    if member.role == ORG_ROLE_OWNER:
        if await _count_owners(db, organization_id) <= 1:
            raise OrganizationServiceError("last_owner_protection")

    await db.delete(member)
    await db.flush()


__all__ = [
    "OrganizationServiceError",
    "list_user_organizations",
    "get_organization",
    "list_members",
    "create_organization",
    "update_organization",
    "delete_organization",
    "invite_member",
    "update_member_role",
    "remove_member",
]
