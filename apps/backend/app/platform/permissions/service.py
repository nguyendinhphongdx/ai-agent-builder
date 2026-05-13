"""Permission resolution + check helpers.

Two tiers, mirroring the role bindings in ``roles.py``:

  ORG-scoped perms       checked via ``has_org_permission_async``
                          against the user's ``organization_members.role``.

  WORKSPACE-scoped perms checked via ``has_workspace_permission_async``
                          (or the legacy ``has_permission_async``)
                          against the EFFECTIVE workspace role —
                          a function of both org role and
                          workspace_members.role (see
                          :func:`roles.effective_workspace_role`).

Custom roles still resolve via the ``custom_roles`` table by slug;
the slug lives on ``workspace_members.role`` and is workspace-scoped.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.custom_role import CustomRole
from app.models.organization_member import ORG_ROLES, OrganizationMember
from app.models.workspace import Workspace
from app.models.workspace_member import WORKSPACE_ROLES, WorkspaceMember
from app.platform.permissions.catalogue import (
    is_known_permission,
    is_org_permission,
)
from app.platform.permissions.roles import (
    ORG_ROLE_BINDINGS,
    WORKSPACE_ROLE_BINDINGS,
    effective_workspace_role,
)

logger = logging.getLogger("agentforge")


# ─── Org-tier check ────────────────────────────────────────────────


async def has_org_permission_async(
    db: AsyncSession,
    user_id: uuid.UUID,
    organization_id: uuid.UUID,
    permission: str,
) -> bool:
    """True iff the user has ``permission`` at the org tier.

    Only valid for permissions in
    :data:`app.platform.permissions.catalogue.ORG_PERMISSIONS`.
    """
    if not is_org_permission(permission):
        raise ValueError(
            f"{permission!r} is not an org-scoped permission — "
            "use has_workspace_permission_async instead."
        )
    role = await _get_org_role(db, organization_id, user_id)
    if role is None or role not in ORG_ROLES:
        return False
    return permission in ORG_ROLE_BINDINGS.get(role, frozenset())


# ─── Workspace-tier check ──────────────────────────────────────────


async def has_workspace_permission_async(
    db: AsyncSession,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    permission: str,
) -> bool:
    """True iff the user has ``permission`` in ``workspace_id``.

    Combines the org-tier role (organization_members) and the
    per-workspace role (workspace_members) via
    :func:`effective_workspace_role`. Custom workspace-roles still
    work — they're resolved by slug at workspace_members.role.
    """
    if is_org_permission(permission):
        raise ValueError(
            f"{permission!r} is an org-scoped permission — "
            "use has_org_permission_async instead."
        )
    if not is_known_permission(permission):
        raise ValueError(f"Unknown permission: {permission!r}")

    # Get the workspace + its org in one round-trip.
    org_id = await db.scalar(
        select(Workspace.organization_id).where(Workspace.id == workspace_id)
    )
    if org_id is None:
        return False

    org_role = await _get_org_role(db, org_id, user_id)
    if org_role is None:
        return False

    ws_role = await db.scalar(
        select(WorkspaceMember.role).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )

    # Built-in role path — clean, no DB.
    if ws_role is None or ws_role in WORKSPACE_ROLES:
        eff = effective_workspace_role(org_role, ws_role)
        if eff is None:
            return False
        return permission in WORKSPACE_ROLE_BINDINGS.get(eff, frozenset())

    # Custom workspace-role: resolve by slug. The org-admin override
    # still applies — an org owner/admin gets implicit owner/admin
    # regardless of the custom slug.
    if org_role in ("owner", "admin"):
        eff = effective_workspace_role(org_role, None)
        return permission in WORKSPACE_ROLE_BINDINGS.get(eff, frozenset())

    custom = await db.scalar(
        select(CustomRole).where(
            CustomRole.organization_id == org_id,
            CustomRole.slug == ws_role,
        )
    )
    if custom is None:
        logger.warning(
            "permissions: workspace %s member %s carries unknown role slug %r",
            workspace_id, user_id, ws_role,
        )
        return False
    return permission in (custom.permissions or [])


# ─── Legacy alias kept for one or two call sites that pass the
#     WorkspaceMember row instead of looking up by ids. ──────────────


def has_permission(member: WorkspaceMember, permission: str) -> bool:
    """Sync check ignoring org-tier overrides. Use only when you're
    sure the workspace member's row carries the final role (no org-
    admin force). For request-time checks, prefer the async variant."""
    if not is_known_permission(permission):
        raise ValueError(f"Unknown permission: {permission!r}")
    return permission in WORKSPACE_ROLE_BINDINGS.get(member.role, frozenset())


async def has_permission_async(
    db: AsyncSession,
    member: WorkspaceMember,
    permission: str,
) -> bool:
    """Workspace-tier check by row. Thin wrapper around
    :func:`has_workspace_permission_async`."""
    return await has_workspace_permission_async(
        db, member.user_id, member.workspace_id, permission
    )


# ─── Helpers ───────────────────────────────────────────────────────


async def _get_org_role(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> str | None:
    return await db.scalar(
        select(OrganizationMember.role).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )


__all__ = [
    "has_org_permission_async",
    "has_workspace_permission_async",
    "has_permission",
    "has_permission_async",
]
