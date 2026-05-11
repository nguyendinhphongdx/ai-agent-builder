"""Permission resolution + check helpers.

The hot path is ``has_permission(member, perm)``: a single dict
lookup. Custom roles (Block 3) will extend this with a DB read,
cached per request.
"""
from __future__ import annotations

from app.models.workspace_member import WorkspaceMember
from app.permissions.catalogue import is_known_permission
from app.permissions.roles import role_permissions


def has_permission(member: WorkspaceMember, permission: str) -> bool:
    """True iff the member's role grants ``permission``.

    Unknown permissions return False — fail-closed (and the catalogue
    check below would raise in dev to catch typos early).
    """
    if not is_known_permission(permission):
        # In dev/CI this is a typo at the call site — make it loud.
        raise ValueError(f"Unknown permission: {permission!r}")
    return permission in role_permissions(member.role)


__all__ = ["has_permission"]
