"""Plugin / Extension System (P3.1 MVP — manifest + registry only).

Future blocks fill in the execution layer:
  - Plugin Daemon: subprocess pool, per-runtime workers.
  - Sandbox: Linux namespaces + seccomp + cgroups via the
    existing code-sandbox service.
  - Tool integration: plugin-declared tools auto-register in
    the workspace's tool catalogue.

Today: install / list / uninstall registration rows from
plugin.yaml manifests.
"""
