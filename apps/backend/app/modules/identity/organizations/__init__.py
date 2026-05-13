"""Organizations module — CRUD on the tenant root + member ops.

The personal-org auto-creation at signup lives in
``app.modules.identity.workspaces.service.ensure_personal_workspace``
because the two are paired (an org without a workspace is a useless
shell). This module owns the *multi-user* surface: invite, promote,
remove, settings.
"""
