"""Permission catalogue — every fine-grained capability a user might
exercise.

Two scopes:
  * ORG_*       checked against the user's role in
                ``organization_members`` (the tenant-wide tier).
  * everything else
                checked against the EFFECTIVE workspace role
                (org-admin force / org-viewer clamp — see
                ``app.platform.permissions.roles.effective_workspace_role``).

Convention: ``<resource>.<verb>``. Wildcards (``agent.*``, ``*.read``)
are NOT supported — explicit per-permission grants only, so the audit
log records exactly which permission a role/user actually has.

When adding a permission:
  1. Add the string constant here in the right scope section.
  2. Wire it into the built-in roles in ``roles.py``.
  3. Add ``require_workspace_permission(...)`` or
     ``require_org_permission(...)`` to the endpoint(s) that need it.
"""
from __future__ import annotations

# ═════════════════════════════════════════════════════════════════
# ORG-SCOPED permissions — granted by ``organization_members.role``
# ═════════════════════════════════════════════════════════════════

# ─── Org membership management ────────────────────────────────────
ORG_MEMBER_READ = "org.member.read"
ORG_MEMBER_INVITE = "org.member.invite"
ORG_MEMBER_ROLE_CHANGE = "org.member.role_change"
ORG_MEMBER_REMOVE = "org.member.remove"

# ─── Workspace lifecycle (creating new projects in the org) ───────
ORG_WORKSPACE_CREATE = "org.workspace.create"
ORG_WORKSPACE_DELETE = "org.workspace.delete"

# ─── Org settings / lifecycle ─────────────────────────────────────
ORG_SETTINGS_READ = "org.settings.read"
ORG_SETTINGS_UPDATE = "org.settings.update"
ORG_DELETE = "org.delete"

# ─── Org-tier integrations (identity + compliance) ────────────────
SSO_CONFIGURE = "org.sso.configure"
SCIM_TOKEN_MANAGE = "org.scim.token.manage"
IP_RULE_MANAGE = "org.ip_rule.manage"
BILLING_MANAGE = "org.billing.manage"
AUDIT_READ = "org.audit.read"


# ═════════════════════════════════════════════════════════════════
# WORKSPACE-SCOPED permissions — granted by effective workspace role
# ═════════════════════════════════════════════════════════════════

# ─── Agents ────────────────────────────────────────────────────────
AGENT_READ = "agent.read"
AGENT_CREATE = "agent.create"
AGENT_UPDATE = "agent.update"
AGENT_DELETE = "agent.delete"
AGENT_PUBLISH = "agent.publish"
AGENT_CHAT = "agent.chat"

# ─── Knowledge bases ───────────────────────────────────────────────
KB_READ = "kb.read"
KB_CREATE = "kb.create"
KB_UPDATE = "kb.update"
KB_DELETE = "kb.delete"
KB_DOCUMENT_UPLOAD = "kb.document.upload"
KB_DOCUMENT_DELETE = "kb.document.delete"

# ─── Tools ─────────────────────────────────────────────────────────
TOOL_READ = "tool.read"
TOOL_CREATE = "tool.create"
TOOL_UPDATE = "tool.update"
TOOL_DELETE = "tool.delete"
TOOL_EXECUTE = "tool.execute"

# ─── Workflows ─────────────────────────────────────────────────────
WORKFLOW_READ = "workflow.read"
WORKFLOW_CREATE = "workflow.create"
WORKFLOW_UPDATE = "workflow.update"
WORKFLOW_DELETE = "workflow.delete"
WORKFLOW_EXECUTE = "workflow.execute"
WORKFLOW_SCHEDULE = "workflow.schedule"

# ─── Conversations ─────────────────────────────────────────────────
CONVERSATION_READ = "conversation.read"
CONVERSATION_DELETE = "conversation.delete"

# ─── Credentials (LLM provider keys — high-sensitivity) ───────────
CREDENTIAL_READ = "credential.read"   # masked preview, not plaintext
CREDENTIAL_CREATE = "credential.create"
CREDENTIAL_DELETE = "credential.delete"

# ─── Workspace membership (per-project ACL) ───────────────────────
MEMBER_READ = "workspace.member.read"
MEMBER_INVITE = "workspace.member.invite"
MEMBER_ROLE_CHANGE = "workspace.member.role_change"
MEMBER_REMOVE = "workspace.member.remove"

# ─── Workspace settings ────────────────────────────────────────────
WORKSPACE_SETTINGS_READ = "workspace.settings.read"
WORKSPACE_SETTINGS_UPDATE = "workspace.settings.update"
WORKSPACE_DELETE = "workspace.delete"

# ─── Personal access tokens ────────────────────────────────────────
PAT_READ = "pat.read"
PAT_MANAGE = "pat.manage"


# ═════════════════════════════════════════════════════════════════
# Sets — used by validation + the ``require_*`` factories to
# dispatch a perm string to the right binding table.
# ═════════════════════════════════════════════════════════════════

ORG_PERMISSIONS: frozenset[str] = frozenset(
    {
        ORG_MEMBER_READ, ORG_MEMBER_INVITE, ORG_MEMBER_ROLE_CHANGE, ORG_MEMBER_REMOVE,
        ORG_WORKSPACE_CREATE, ORG_WORKSPACE_DELETE,
        ORG_SETTINGS_READ, ORG_SETTINGS_UPDATE, ORG_DELETE,
        SSO_CONFIGURE, SCIM_TOKEN_MANAGE, IP_RULE_MANAGE, BILLING_MANAGE, AUDIT_READ,
    }
)

WORKSPACE_PERMISSIONS: frozenset[str] = frozenset(
    {
        AGENT_READ, AGENT_CREATE, AGENT_UPDATE, AGENT_DELETE, AGENT_PUBLISH, AGENT_CHAT,
        KB_READ, KB_CREATE, KB_UPDATE, KB_DELETE, KB_DOCUMENT_UPLOAD, KB_DOCUMENT_DELETE,
        TOOL_READ, TOOL_CREATE, TOOL_UPDATE, TOOL_DELETE, TOOL_EXECUTE,
        WORKFLOW_READ, WORKFLOW_CREATE, WORKFLOW_UPDATE, WORKFLOW_DELETE,
        WORKFLOW_EXECUTE, WORKFLOW_SCHEDULE,
        CONVERSATION_READ, CONVERSATION_DELETE,
        CREDENTIAL_READ, CREDENTIAL_CREATE, CREDENTIAL_DELETE,
        MEMBER_READ, MEMBER_INVITE, MEMBER_ROLE_CHANGE, MEMBER_REMOVE,
        WORKSPACE_SETTINGS_READ, WORKSPACE_SETTINGS_UPDATE, WORKSPACE_DELETE,
        PAT_READ, PAT_MANAGE,
    }
)


ALL_PERMISSIONS: tuple[str, ...] = tuple(
    sorted(ORG_PERMISSIONS | WORKSPACE_PERMISSIONS)
)


def is_known_permission(perm: str) -> bool:
    return perm in ORG_PERMISSIONS or perm in WORKSPACE_PERMISSIONS


def is_org_permission(perm: str) -> bool:
    """Used by ``require_*`` factories to pick the right binding."""
    return perm in ORG_PERMISSIONS
