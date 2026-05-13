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

from app.models.user import User
from app.models.workspace_member import (
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLE_VIEWER,
    WorkspaceMember,
)
from app.modules.identity.auth.dependencies import get_current_user
from app.modules.identity.workspaces.service import get_member
from app.platform.db.session import get_db
from app.platform.permissions.service import (
    has_org_permission_async,
    has_permission_async,
)

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
    """Dependency factory — 403 unless the caller has ``permission``
    in the workspace named by the path's ``workspace_id``.

    Use on endpoints whose path already carries ``workspace_id``
    (workspace-scoped CRUD under ``/workspaces/{id}/...``).
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
        if not await has_permission_async(db, member, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return member

    return _check


def require_active_permission(permission: str):
    """Dependency factory — 403 unless the caller has ``permission``
    in their **active** workspace (the one set on the request via
    X-Workspace-Id header or user.default_workspace_id).

    Use this for endpoints whose URL doesn't carry workspace_id —
    most resource CRUD lives under ``/agents``, ``/knowledge-bases``,
    etc. and gets its tenant scope from the request's active workspace.

    Resolution:
      1. get_current_user (already runs) seeds ``current_workspace_id``
         in the ContextVar.
      2. This dep reads it back and looks up the matching member row.
      3. Permission check + return the member.

    No active workspace context (background tasks, pre-backfilled
    legacy users) → 403 with ``no_active_workspace``. UI should
    surface a workspace-picker prompt.
    """

    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> WorkspaceMember:
        from app.platform.context import current_workspace_id_or_none

        workspace_id = current_workspace_id_or_none()
        if workspace_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="no_active_workspace",
            )

        member = await get_member(db, workspace_id, current_user.id)
        if member is None:
            # User isn't a member of the workspace they're trying to
            # act in — auth dep accepted them (default workspace) but
            # the header is overriding to one they don't belong to.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not_a_workspace_member",
            )
        if not await has_permission_async(db, member, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return member

    return _check


def require_org_permission(permission: str):
    """Dependency factory — 403 unless the caller has the ORG-tier
    ``permission`` in the request's active organization.

    Resolution:
      1. ``get_current_user`` seeds ``current_organization_id`` in the
         ContextVar from X-Organization-Id header or the active
         workspace's parent (else ``user.default_organization_id``).
      2. This dep reads it back, looks up ``organization_members.role``
         for ``(user_id, org_id)``, checks ``ORG_ROLE_BINDINGS``.

    No active org context (background tasks, freshly-signed-up users
    before personal_org backfill) → 403 with ``no_active_organization``.
    """

    async def _check(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> uuid.UUID:
        from app.platform.context import current_organization_id_or_none

        organization_id = current_organization_id_or_none()
        if organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="no_active_organization",
            )

        ok = await has_org_permission_async(
            db, current_user.id, organization_id, permission
        )
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing org permission: {permission}",
            )
        return organization_id

    return _check
