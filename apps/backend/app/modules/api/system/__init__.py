"""System (root) org surface — Base.vn-style platform admin.

Gates every endpoint with :func:`require_platform_admin`: caller must
be an owner/admin of the org with ``slug='system'``. This is THE
surface a customer-facing SaaS operator uses to:

  * list, create, suspend, delete customer orgs
  * impersonate a user inside a customer org (audit-logged)
  * (future) manage packages, subscriptions, contracts

Distinct from ``modules.api.admin`` (Hub moderation gated on
``users.role`` hierarchy). The two surfaces can merge once the
``users.role`` column is fully retired.
"""
