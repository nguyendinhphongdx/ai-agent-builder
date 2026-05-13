# Plugins

Reference plugins + the contract for third-party plugin authors.

## What ships today (P3.1 MVP)

- **Manifest schema** — `apps/backend/app/modules/studio/plugins/manifest.py`
  validates `plugin.yaml` files. Required fields: `id`, `version`
  (semver), `name`, `runtime` (one of `python` / `nodejs` /
  `docker`). Optional: `description`, `entrypoint`,
  `capabilities`, `permissions`, `tools`.
- **Registry table** — `plugins` table + `Plugin` model store
  installed plugins per workspace.
- **CRUD API**:
  - `GET /api/plugins` — list installed
  - `POST /api/plugins/install` — body `{ manifest_yaml }` or
    `{ manifest: {...} }`
  - `PATCH /api/plugins/{id}/status` — enable / disable
  - `DELETE /api/plugins/{id}` — uninstall
- **Sample plugin** — `plugins/sample-echo/` is a working
  reference (echo tool, no permissions).

## What ships later (full P3.1)

- **Plugin Daemon** — subprocess pool that runs plugin code in
  isolated workers. Routes `tool.call` RPC to the matching
  plugin worker.
- **Sandbox** — Linux namespaces + seccomp + cgroups via the
  existing `services/code-sandbox`. Enforces
  `permissions.http_outbound` + `permissions.secrets`.
- **Tool integration** — `capabilities: [tool]` plugins
  auto-register their `tools[]` in the workspace's tool catalogue
  so workflow + agent nodes can call them.
- **Plugin marketplace** — separate from the template
  marketplace, with review + signing.

## Manifest contract

See `plugin.yaml` schema in `app/plugins/manifest.py`. Minimal:

```yaml
id: my-plugin                 # lowercase-kebab, max 64 chars
version: 1.0.0                # semver
name: My Plugin
description: One-line summary.
runtime: python               # python | nodejs | docker
entrypoint: main.py
capabilities:
  - tool                      # tool | trigger | extractor | exporter
permissions:
  http_outbound: []           # whitelisted hosts
  secrets: []                 # secret names plugin may read
tools:                        # only when "tool" in capabilities
  - name: my_tool
    description: What it does.
    input_schema: { type: object, properties: {...} }
    output_schema: { type: object, properties: {...} }
```

Install via the API:

```bash
curl -X POST $API_BASE/api/plugins/install \
  -H "Content-Type: application/json" \
  --cookie "access_token=..." \
  -d "$(jq -Rn --arg yaml "$(cat plugin.yaml)" '{manifest_yaml: $yaml}')"
```
