"""Platform-level role hierarchy.

Orthogonal to any future tenant/workspace role — this controls who can
operate the platform itself (suspend hub templates, refund purchases,
ban abusive users). A logged-in customer is always ``user``.

Hierarchy: user < moderator < support < admin
- ``user``      Default — owns their resources only.
- ``moderator`` Hub moderation: feature templates, suspend reported ones.
- ``support``   Billing + customer ops: refunds, view all purchases, ban
                spam users. Inherits everything ``moderator`` can do.
- ``admin``     Full access. Grants/revokes roles, deletes users.

If we ever need "support but NOT moderator", migrate to permission flags.
For now hierarchy matches real org structure (admins are a strict superset).
"""
from __future__ import annotations

import enum
import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.organization_member import (
    ORG_ROLE_ADMIN,
    ORG_ROLE_OWNER,
    OrganizationMember,
)
from app.models.user import User
from app.modules.identity.auth.dependencies import get_current_user
from app.platform.db.session import get_db


class UserRole(str, enum.Enum):
    USER = "user"
    MODERATOR = "moderator"
    SUPPORT = "support"
    ADMIN = "admin"


# Order = privilege ascending. Higher index ⇒ more privileges.
_HIERARCHY: list[UserRole] = [
    UserRole.USER,
    UserRole.MODERATOR,
    UserRole.SUPPORT,
    UserRole.ADMIN,
]


def _rank(role: str) -> int:
    """Return privilege rank for a role string. Unknown → -1 (denied)."""
    try:
        return _HIERARCHY.index(UserRole(role))
    except ValueError:
        return -1


def has_role(user_role: str, required: UserRole) -> bool:
    """Pure check — useful for conditional UI / branching outside FastAPI deps."""
    return _rank(user_role) >= _rank(required.value)


def require_role(min_role: UserRole):
    """FastAPI dependency factory — gate an endpoint on minimum role.

    Order matters in the endpoint signature: declare ``Depends(get_current_user)``
    first (or rely on a router-level dep) so the contextvar is set; otherwise
    this dep can't read the user.

    Usage:
        @router.patch(
            "/admin/templates/{id}",
            dependencies=[Depends(require_role(UserRole.MODERATOR))],
        )
    """

    async def _check(
        _: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        # We re-read the User row instead of trusting a cached role on the
        # JWT — admin demotion should take effect immediately, not after the
        # token expires.
        from app.platform.context import current_user_id

        user = await db.get(User, current_user_id())
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        if not has_role(user.role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {min_role.value} role or higher",
            )

    return _check


# ─── System (root) org membership ──────────────────────────────────
# Base.vn-style: the platform owner runs from one designated org
# (slug='system'). Its members are the staff who can manage every
# customer org, subscription, contract, etc. Gating ``/system/*``
# endpoints on this membership keeps the platform-admin role inside
# the same data model as everything else — no second special-case
# auth surface.


async def _system_org_role(
    db: AsyncSession, user_id: uuid.UUID
) -> str | None:
    """Return the user's role in the system org, or None if not a member.

    Source of truth is ``organizations.is_system = true`` — the partial
    unique index guarantees at most one such row exists.
    """
    return await db.scalar(
        select(OrganizationMember.role)
        .join(
            Organization,
            Organization.id == OrganizationMember.organization_id,
        )
        .where(
            Organization.is_system.is_(True),
            OrganizationMember.user_id == user_id,
        )
    )


async def is_platform_admin(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """True when ``user_id`` is an owner/admin of the system org.

    Cheap — one indexed join. Safe to call inside per-request paths.
    """
    role = await _system_org_role(db, user_id)
    return role in (ORG_ROLE_OWNER, ORG_ROLE_ADMIN)


def require_platform_admin():
    """FastAPI dep — gate ``/api/system/*`` on system-org admin membership.

    Falls back to the old ``UserRole.ADMIN`` check so deployments that
    haven't run ``seed_root_org`` yet keep working with the previous
    ``users.role=admin`` model. Once everyone has migrated this fallback
    can be dropped.
    """

    async def _check(
        _: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        from app.platform.context import current_user_id

        user_id = current_user_id()
        if await is_platform_admin(db, user_id):
            return
        # Back-compat fallback while migrating away from users.role.
        user = await db.get(User, user_id)
        if user is not None and has_role(user.role, UserRole.ADMIN):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires platform admin (system org membership)",
        )

    return _check


def require_system_org_member():
    """Looser gate — any role in the system org (incl. viewer/editor).

    Use for read-only ``/system/*`` endpoints where mods/support need
    visibility but shouldn't mutate (e.g. staff dashboard).
    """

    async def _check(
        _: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        from app.platform.context import current_user_id

        if (await _system_org_role(db, current_user_id())) is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of the system org",
            )

    return _check
