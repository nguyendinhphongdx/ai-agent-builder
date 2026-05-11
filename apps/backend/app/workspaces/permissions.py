"""Workspace-scoped permission dependencies.

Two complementary primitives for gating endpoints:

  - :func:`require_workspace_role` enforces a minimum role rank.
    Use for endpoints whose meaning is "this is an admin op" —
    member management, billing, danger-zone ops.
  - :func:`require_permission` (Phase 1.5) enforces a specific
    fine-grained permission flag. Use for resource CRUD — lets
    custom roles grant a narrow capability without promoting to
    a full role tier.

Both return the resolved :class:`WorkspaceMember`. Pick whichever
matches the endpoint's *intent* — many existing routes lean on
role checks and stay simple that way.
"""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workspace_member import (
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLE_VIEWER,
    WorkspaceMember,
)
from app.permissions.service import has_permission
from app.workspaces.service import get_member


# Ordered low → high. ``rank[role]`` gives the integer rank used by
# the comparison in ``require_workspace_role``.
_ROLE_RANK = {
    WORKSPACE_ROLE_VIEWER: 0,
    WORKSPACE_ROLE_EDITOR: 1,
    WORKSPACE_ROLE_ADMIN: 2,
    WORKSPACE_ROLE_OWNER: 3,
}


def role_at_least(role: str, min_role: str) -> bool:
    """Compare two role strings by rank. Unknown roles read as below
    every known role — safer default than throwing here."""
    return _ROLE_RANK.get(role, -1) >= _ROLE_RANK[min_role]


def require_workspace_role(min_role: str):
    """Dependency factory — 403 unless caller is a member with role
    ``>= min_role``. Returns the resolved :class:`WorkspaceMember`.

    The endpoint must declare ``workspace_id: uuid.UUID`` as a path
    parameter; FastAPI auto-injects it into this sub-dep so we can
    look up the membership row in a single query.
    """
    if min_role not in _ROLE_RANK:
        raise ValueError(f"Unknown role: {min_role}")

    async def _check(
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> WorkspaceMember:
        member = await get_member(db, workspace_id, current_user.id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
        if not role_at_least(member.role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role {min_role} or higher; you have {member.role}",
            )
        return member

    return _check


def require_permission(permission: str):
    """Dependency factory — 403 unless the caller has ``permission``.

    Resolves the caller's WorkspaceMember from the path's
    ``workspace_id`` (FastAPI auto-injects via sub-dep), then checks
    :func:`app.permissions.service.has_permission` against the
    member's role.

    Same shape as :func:`require_workspace_role`: returns the
    WorkspaceMember on success, raises 404 / 403 otherwise. 404 for
    non-members keeps cross-tenant ids opaque (no "this exists but
    you can't see it" leak).
    """

    async def _check(
        workspace_id: uuid.UUID,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> WorkspaceMember:
        member = await get_member(db, workspace_id, current_user.id)
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )
        if not has_permission(member, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return member

    return _check
