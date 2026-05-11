"""Permission catalogue — every fine-grained capability a workspace
member might be granted.

Convention: ``<resource>.<verb>``. Wildcards (``agent.*``, ``*.read``)
are NOT supported — explicit per-permission grants only, so the
audit log records exactly which permission a role/user actually has.

When adding a permission:
  1. Add the string constant here.
  2. Wire it into the built-in roles in roles.py.
  3. Add ``require_permission(...)`` to the endpoint(s) that need it.
"""
from __future__ import annotations

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
WORKFLOW_SCHEDULE = "workflow.schedule"  # manage cron triggers

# ─── Conversations ─────────────────────────────────────────────────
CONVERSATION_READ = "conversation.read"
CONVERSATION_DELETE = "conversation.delete"

# ─── Credentials (LLM provider keys — high-sensitivity) ───────────
CREDENTIAL_READ = "credential.read"   # masked preview, not plaintext
CREDENTIAL_CREATE = "credential.create"
CREDENTIAL_DELETE = "credential.delete"

# ─── Workspace administration ─────────────────────────────────────
MEMBER_READ = "member.read"
MEMBER_INVITE = "member.invite"
MEMBER_ROLE_CHANGE = "member.role_change"
MEMBER_REMOVE = "member.remove"
WORKSPACE_SETTINGS_READ = "workspace.settings.read"
WORKSPACE_SETTINGS_UPDATE = "workspace.settings.update"
WORKSPACE_DELETE = "workspace.delete"

# ─── Org-level (SSO / SCIM / IP rules / billing) ──────────────────
SSO_CONFIGURE = "sso.configure"
SCIM_TOKEN_MANAGE = "scim.token.manage"
IP_RULE_MANAGE = "ip_rule.manage"
BILLING_MANAGE = "billing.manage"

# ─── Personal access tokens + integrations ────────────────────────
PAT_READ = "pat.read"
PAT_MANAGE = "pat.manage"

# ─── Audit log ─────────────────────────────────────────────────────
AUDIT_READ = "audit.read"


# Master list — used by validation when a custom role tries to grant
# an unknown permission. Keep ordered for predictable serialisation
# in API responses.
ALL_PERMISSIONS: tuple[str, ...] = (
    AGENT_READ, AGENT_CREATE, AGENT_UPDATE, AGENT_DELETE, AGENT_PUBLISH, AGENT_CHAT,
    KB_READ, KB_CREATE, KB_UPDATE, KB_DELETE, KB_DOCUMENT_UPLOAD, KB_DOCUMENT_DELETE,
    TOOL_READ, TOOL_CREATE, TOOL_UPDATE, TOOL_DELETE, TOOL_EXECUTE,
    WORKFLOW_READ, WORKFLOW_CREATE, WORKFLOW_UPDATE, WORKFLOW_DELETE,
    WORKFLOW_EXECUTE, WORKFLOW_SCHEDULE,
    CONVERSATION_READ, CONVERSATION_DELETE,
    CREDENTIAL_READ, CREDENTIAL_CREATE, CREDENTIAL_DELETE,
    MEMBER_READ, MEMBER_INVITE, MEMBER_ROLE_CHANGE, MEMBER_REMOVE,
    WORKSPACE_SETTINGS_READ, WORKSPACE_SETTINGS_UPDATE, WORKSPACE_DELETE,
    SSO_CONFIGURE, SCIM_TOKEN_MANAGE, IP_RULE_MANAGE, BILLING_MANAGE,
    PAT_READ, PAT_MANAGE,
    AUDIT_READ,
)


def is_known_permission(perm: str) -> bool:
    return perm in ALL_PERMISSIONS
