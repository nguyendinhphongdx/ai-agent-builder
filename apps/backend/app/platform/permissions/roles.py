"""Built-in role → permission mappings + effective-role resolution.

Two binding tables — one per scope:

  ORG_ROLE_BINDINGS         role → org-scoped perms
  WORKSPACE_ROLE_BINDINGS   role → workspace-scoped perms

The 4 role names (viewer < editor < admin < owner) are reused in both
tables to keep the mental model symmetric. Higher roles INCLUDE the
lower role's set inside their own scope.

Effective workspace role
─────────────────────────
A user can have BOTH an org role AND a workspace role. We compute
the effective workspace role at request time:

  org owner   → forces workspace ``owner`` everywhere (override)
  org admin   → forces workspace ``admin`` everywhere (override)
  org editor  → workspace_members.role decides freely
  org viewer  → clamps workspace role down to ``viewer`` (ceiling)
  no org membership → no access

This is what makes "Acme's admin can manage every project inside
Acme" work without explicit workspace_members rows, while still
allowing org-editor users to be project-owner of just one workspace.
"""
from __future__ import annotations

from app.models.organization_member import (
    ORG_ROLE_ADMIN,
    ORG_ROLE_EDITOR,
    ORG_ROLE_OWNER,
    ORG_ROLE_VIEWER,
)
from app.models.workspace_member import (
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLE_VIEWER,
)
from app.platform.permissions import catalogue as P

# ═════════════════════════════════════════════════════════════════
# Workspace-scoped role bindings — same as before
# ═════════════════════════════════════════════════════════════════

_VIEWER_PERMISSIONS: frozenset[str] = frozenset(
    {
        P.AGENT_READ, P.AGENT_CHAT,
        P.KB_READ,
        P.TOOL_READ,
        P.WORKFLOW_READ,
        P.CONVERSATION_READ,
        P.MEMBER_READ,
        P.WORKSPACE_SETTINGS_READ,
        P.PAT_READ,
    }
)

_EDITOR_ADDS: frozenset[str] = frozenset(
    {
        P.AGENT_CREATE, P.AGENT_UPDATE, P.AGENT_DELETE, P.AGENT_PUBLISH,
        P.KB_CREATE, P.KB_UPDATE, P.KB_DELETE,
        P.KB_DOCUMENT_UPLOAD, P.KB_DOCUMENT_DELETE,
        P.TOOL_CREATE, P.TOOL_UPDATE, P.TOOL_DELETE, P.TOOL_EXECUTE,
        P.WORKFLOW_CREATE, P.WORKFLOW_UPDATE, P.WORKFLOW_DELETE,
        P.WORKFLOW_EXECUTE,
        P.CONVERSATION_DELETE,
        P.PAT_MANAGE,  # users manage their own PATs from editor up
    }
)
_EDITOR_PERMISSIONS: frozenset[str] = _VIEWER_PERMISSIONS | _EDITOR_ADDS

_ADMIN_ADDS: frozenset[str] = frozenset(
    {
        P.MEMBER_INVITE, P.MEMBER_ROLE_CHANGE, P.MEMBER_REMOVE,
        P.WORKSPACE_SETTINGS_UPDATE,
        P.WORKFLOW_SCHEDULE,
    }
)
_ADMIN_PERMISSIONS: frozenset[str] = _EDITOR_PERMISSIONS | _ADMIN_ADDS

_OWNER_ADDS: frozenset[str] = frozenset(
    {
        P.WORKSPACE_DELETE,
        # Credentials live at owner-tier inside a workspace since they
        # hold plaintext-equivalent LLM API keys. Org-tier secrets
        # (SSO, SCIM, billing) live in ORG_ROLE_BINDINGS below.
        P.CREDENTIAL_READ, P.CREDENTIAL_CREATE, P.CREDENTIAL_DELETE,
    }
)
_OWNER_PERMISSIONS: frozenset[str] = _ADMIN_PERMISSIONS | _OWNER_ADDS


WORKSPACE_ROLE_BINDINGS: dict[str, frozenset[str]] = {
    WORKSPACE_ROLE_VIEWER: _VIEWER_PERMISSIONS,
    WORKSPACE_ROLE_EDITOR: _EDITOR_PERMISSIONS,
    WORKSPACE_ROLE_ADMIN: _ADMIN_PERMISSIONS,
    WORKSPACE_ROLE_OWNER: _OWNER_PERMISSIONS,
}


# ═════════════════════════════════════════════════════════════════
# Org-scoped role bindings — new
# ═════════════════════════════════════════════════════════════════

_ORG_VIEWER_PERMISSIONS: frozenset[str] = frozenset(
    {
        P.ORG_MEMBER_READ,
        P.ORG_SETTINGS_READ,
    }
)

_ORG_EDITOR_ADDS: frozenset[str] = frozenset(
    set()  # plain "joined the org" — workspace-tier creation is admin+
)
_ORG_EDITOR_PERMISSIONS: frozenset[str] = (
    _ORG_VIEWER_PERMISSIONS | _ORG_EDITOR_ADDS
)

_ORG_ADMIN_ADDS: frozenset[str] = frozenset(
    {
        P.ORG_MEMBER_INVITE, P.ORG_MEMBER_REMOVE,
        P.ORG_WORKSPACE_CREATE, P.ORG_WORKSPACE_DELETE,
        P.ORG_SETTINGS_UPDATE,
        P.AUDIT_READ,
        P.IP_RULE_MANAGE,
    }
)
_ORG_ADMIN_PERMISSIONS: frozenset[str] = (
    _ORG_EDITOR_PERMISSIONS | _ORG_ADMIN_ADDS
)

_ORG_OWNER_ADDS: frozenset[str] = frozenset(
    {
        P.ORG_MEMBER_ROLE_CHANGE,
        P.ORG_DELETE,
        P.SSO_CONFIGURE,
        P.SCIM_TOKEN_MANAGE,
        P.BILLING_MANAGE,
    }
)
_ORG_OWNER_PERMISSIONS: frozenset[str] = (
    _ORG_ADMIN_PERMISSIONS | _ORG_OWNER_ADDS
)


ORG_ROLE_BINDINGS: dict[str, frozenset[str]] = {
    ORG_ROLE_VIEWER: _ORG_VIEWER_PERMISSIONS,
    ORG_ROLE_EDITOR: _ORG_EDITOR_PERMISSIONS,
    ORG_ROLE_ADMIN: _ORG_ADMIN_PERMISSIONS,
    ORG_ROLE_OWNER: _ORG_OWNER_PERMISSIONS,
}


# ═════════════════════════════════════════════════════════════════
# Effective workspace role rule
# ═════════════════════════════════════════════════════════════════

_ROLE_RANK = {
    WORKSPACE_ROLE_VIEWER: 1,
    WORKSPACE_ROLE_EDITOR: 2,
    WORKSPACE_ROLE_ADMIN: 3,
    WORKSPACE_ROLE_OWNER: 4,
}


def effective_workspace_role(
    org_role: str | None, workspace_role: str | None
) -> str | None:
    """Resolve the effective per-workspace role from the two tier
    inputs. Returns ``None`` to mean "no access" — caller raises 403.

    Rules:
      * Not in the org at all                  → ``None``
      * Org ``owner``                          → force ``owner``
      * Org ``admin``                          → force ``admin``
      * Org ``viewer``                         → clamp to ``viewer``
        (regardless of any workspace_role they may have)
      * Org ``editor`` + no workspace_role     → ``None``
      * Org ``editor`` + workspace_role        → that workspace_role
    """
    if org_role is None:
        return None
    if org_role == ORG_ROLE_OWNER:
        return WORKSPACE_ROLE_OWNER
    if org_role == ORG_ROLE_ADMIN:
        return WORKSPACE_ROLE_ADMIN
    if org_role == ORG_ROLE_VIEWER:
        return WORKSPACE_ROLE_VIEWER
    # org editor: workspace decides.
    return workspace_role


def role_permissions(role: str) -> frozenset[str]:
    """Backwards-compat alias — resolves a WORKSPACE role to its perms.
    New code should call the binding tables directly so the scope is
    explicit at the call site."""
    return WORKSPACE_ROLE_BINDINGS.get(role, frozenset())


# Legacy alias preserved for one or two stragglers that import the old
# name. Will be dropped once those sites migrate to the per-scope tables.
BUILTIN_ROLE_PERMISSIONS = WORKSPACE_ROLE_BINDINGS


__all__ = [
    "ORG_ROLE_BINDINGS",
    "WORKSPACE_ROLE_BINDINGS",
    "BUILTIN_ROLE_PERMISSIONS",
    "effective_workspace_role",
    "role_permissions",
]
