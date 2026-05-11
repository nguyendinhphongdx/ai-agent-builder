"""Built-in role → permission mapping.

Each role gets a frozen set of permissions. Higher roles INCLUDE
the lower role's set, so checks like ``role_at_least`` and
``has_permission`` agree.

  viewer  read-only — no creating, updating, or running anything.
  editor  viewer + create/update/run agents/KB/tools/workflows.
  admin   editor + member management + workspace settings + audit.
          Doesn't include credential mgmt by default (sensitive),
          owner can grant it via custom role.
  owner   admin + workspace delete + billing + SSO + IP rules.

Custom roles (Phase 1.5 Block 3) layer on top — admin can author
roles with any subset of ALL_PERMISSIONS. Members carrying a custom
role get exactly those grants, no inheritance.
"""
from __future__ import annotations

from app.models.workspace_member import (
    WORKSPACE_ROLE_ADMIN,
    WORKSPACE_ROLE_EDITOR,
    WORKSPACE_ROLE_OWNER,
    WORKSPACE_ROLE_VIEWER,
)
from app.permissions import catalogue as P

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
        P.PAT_MANAGE,  # users manage their own PATs even as editors
    }
)
_EDITOR_PERMISSIONS: frozenset[str] = _VIEWER_PERMISSIONS | _EDITOR_ADDS


_ADMIN_ADDS: frozenset[str] = frozenset(
    {
        P.MEMBER_INVITE, P.MEMBER_ROLE_CHANGE, P.MEMBER_REMOVE,
        P.WORKSPACE_SETTINGS_UPDATE,
        P.WORKFLOW_SCHEDULE,
        P.AUDIT_READ,
        P.IP_RULE_MANAGE,
    }
)
_ADMIN_PERMISSIONS: frozenset[str] = _EDITOR_PERMISSIONS | _ADMIN_ADDS


_OWNER_ADDS: frozenset[str] = frozenset(
    {
        P.WORKSPACE_DELETE,
        P.SSO_CONFIGURE,
        P.SCIM_TOKEN_MANAGE,
        P.BILLING_MANAGE,
        # Credentials live at owner-tier by default since they hold
        # plaintext-equivalent LLM API keys.
        P.CREDENTIAL_READ, P.CREDENTIAL_CREATE, P.CREDENTIAL_DELETE,
    }
)
_OWNER_PERMISSIONS: frozenset[str] = _ADMIN_PERMISSIONS | _OWNER_ADDS


# Public mapping. Lookups go through ``role_permissions`` so callers
# don't depend on the underscored names.
BUILTIN_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    WORKSPACE_ROLE_VIEWER: _VIEWER_PERMISSIONS,
    WORKSPACE_ROLE_EDITOR: _EDITOR_PERMISSIONS,
    WORKSPACE_ROLE_ADMIN: _ADMIN_PERMISSIONS,
    WORKSPACE_ROLE_OWNER: _OWNER_PERMISSIONS,
}


def role_permissions(role: str) -> frozenset[str]:
    """Resolve a built-in role string to its permission set. Unknown
    roles return the empty set — fail-closed. Custom roles are
    resolved by the service layer (Block 3) and don't go through here."""
    return BUILTIN_ROLE_PERMISSIONS.get(role, frozenset())
