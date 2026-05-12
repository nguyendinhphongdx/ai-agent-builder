"""ops/ — operational visibility.

  * audit/      audit_logs CRUD (write goes through ``platform.observability``
                helpers; retention sweep lives in ``background.audit_purge``)
  * dashboard/  aggregator endpoints feeding the home page

Future homes for: compliance reports, system-health pages,
admin-only diagnostics that are *informational* (not audience-layer
routes — those go in ``api/admin/``).
"""
