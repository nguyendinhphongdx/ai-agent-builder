"""Platform admin endpoints — gated by platform role hierarchy.

See ``app.modules.identity.auth.permissions`` for the role model. Each endpoint declares
its minimum role; admin (highest) inherits everything below.

Endpoints write to ``admin_actions`` audit log so any moderation /
billing decision can be traced back to the staff member who made it.
"""
