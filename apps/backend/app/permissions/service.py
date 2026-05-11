"""Permission resolution + check helpers.

Built-in roles resolve via :mod:`app.permissions.roles` (a pure
dict). Custom roles resolve via a DB lookup on the ``custom_roles``
table — the slug stored in ``workspace_members.role`` is the lookup
key.

The hot path is ``has_permission(member, perm)`` for built-in roles:
a single dict lookup, no IO. Custom roles add one SELECT per check.
Per-request caching can layer on later (FastAPI request scope) if
this shows up in profiles; not needed at current scale.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_role import CustomRole
from app.models.workspace import Workspace
from app.models.workspace_member import WORKSPACE_ROLES, WorkspaceMember
from app.permissions.catalogue import is_known_permission
from app.permissions.roles import role_permissions

logger = logging.getLogger("agentforge")


def has_permission(member: WorkspaceMember, permission: str) -> bool:
    """Sync-only check against built-in roles.

    Returns ``False`` for custom-role slugs — callers that may
    encounter custom roles must use :func:`has_permission_async`.
    Use this entry point when you've already filtered to built-in
    roles (or are running in a context without DB access).
    """
    if not is_known_permission(permission):
        raise ValueError(f"Unknown permission: {permission!r}")
    return permission in role_permissions(member.role)


async def has_permission_async(
    db: AsyncSession,
    member: WorkspaceMember,
    permission: str,
) -> bool:
    """Async check that resolves both built-in and custom roles.

    Built-ins short-circuit via :func:`has_permission` (no DB hit).
    Custom roles resolve through one ``SELECT`` on ``custom_roles``
    scoped to the workspace's organization.
    """
    if not is_known_permission(permission):
        raise ValueError(f"Unknown permission: {permission!r}")

    # Built-in fast path — no DB.
    if member.role in WORKSPACE_ROLES:
        return permission in role_permissions(member.role)

    # Custom role — look up by (organization_id, slug). We don't have
    # the org id on the member row directly; resolve via the workspace.
    org_id = await db.scalar(
        select(Workspace.organization_id).where(Workspace.id == member.workspace_id)
    )
    if org_id is None:
        return False

    custom = await db.scalar(
        select(CustomRole).where(
            CustomRole.organization_id == org_id,
            CustomRole.slug == member.role,
        )
    )
    if custom is None:
        # Slug stored on the member doesn't resolve — log + deny.
        # Most likely the role was deleted but the member wasn't
        # reassigned. Admins should run a sweep.
        logger.warning(
            "permissions: member %s/%s carries unknown role slug %r",
            member.workspace_id,
            member.user_id,
            member.role,
        )
        return False
    return permission in (custom.permissions or [])


__all__ = ["has_permission", "has_permission_async"]
