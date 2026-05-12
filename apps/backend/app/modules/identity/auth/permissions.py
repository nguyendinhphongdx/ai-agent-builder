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

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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
