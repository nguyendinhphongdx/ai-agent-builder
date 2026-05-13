---
title: Module template (4-layer + when to split)
domain: backend
---

# Module template

Every feature lives under one of the 7 buckets in `app/modules/`:

```
studio/      what users BUILD     (agents, workflows, knowledge, tools, plugins)
runtime/     HOW it activates     (chat, triggers, jobs, notifications, uploads)
identity/    WHO can act          (auth, workspaces, tokens)
integrations/external systems    (connectors, llm, mcp)
commerce/    money flow           (payments, usage, hub)
ops/         visibility           (audit, dashboard)
api/         audience layers      (external, internal, admin)
```

Pick the bucket by asking *"what role does this play?"* — don't invent a
new top-level. Each bucket's `__init__.py` documents what fits.

## Canonical folder shape

```
modules/<bucket>/<feature>/
├── __init__.py        # short docstring + (optional) listener registration
├── router.py          # FastAPI endpoints. Thin: parse request, call service.
├── service.py         # Async business logic. Reads ContextVar, owns SQL.
├── schemas.py         # Pydantic request/response shapes.
└── (model lives in app/models/<entity>.py, imported here as needed)
```

That's it for 90% of features. The remaining 10% earn extra files
based on actual complexity — see "when to split" below.

## Layer contracts

| Layer | Owns | Imports from |
|---|---|---|
| `router.py` | HTTP shape, status codes, dependency injection | `service`, `schemas`, `platform/*` |
| `service.py` | Business rules, SQL, side-effect emission | `models`, `platform/*`, `core/*`, `events` |
| `schemas.py` | Request/response shapes (Pydantic) | stdlib, pydantic |
| `models/*.py` | SQLAlchemy declarative models | `platform.db.Base` |

Rules of thumb:

- **Routers never run raw `select()`.** If you find yourself writing
  SQL there, it belongs in the service.
- **Services read `current_user_id()` from the ContextVar** instead
  of taking `user_id` as a parameter — exceptions documented in
  CLAUDE.md (login flow, workflow runner, ingestion, background tasks).
- **Schemas don't have logic.** No validators that hit the DB; those
  belong in the service.

## When to split files

Split when **the file mixes concerns** — not when it crosses an
arbitrary LOC threshold. Specifically:

### Split `router.py` → subrouters when

- You have more than ~10 endpoints AND they fall into 2+ sub-concerns
  (e.g. auth has basic / mfa / sso / scim / password-reset).
- Look at `modules/identity/auth/sso/` and `scim/` for the pattern.

```
modules/identity/auth/
├── router.py                ← thin: aggregates subrouters
├── service.py
├── schemas.py
├── routers/                 ← introduce when you split
│   ├── basic.py
│   ├── mfa.py
│   ├── password.py
│   └── email_verify.py
└── sso/                     ← bigger subdomain: full feature folder
    ├── router.py
    └── service.py
```

### Split `service.py` → service/ when

- The service touches **3+ aggregate roots** AND each has its own
  CRUD + policy. Workspaces is the canonical case (Workspace +
  Member + Invitation + Organization).

```
modules/identity/workspaces/
└── service/
    ├── __init__.py          ← re-exports for backward compat
    ├── workspace.py         ← Workspace aggregate
    ├── member.py            ← Member aggregate + role policy
    ├── invitation.py        ← Invitation aggregate
    └── bootstrap.py         ← personal-workspace setup
```

Don't split by file size. `service_helpers.py` is the wrong axis —
split by **domain boundary**.

### Add `use_cases/` when

A router endpoint is doing multi-service orchestration with branching
(login → verify → MFA fork → audit → cookies). The use case owns the
flow; the router stays "parse + delegate + render":

```
modules/identity/auth/
└── use_cases/
    ├── login.py
    ├── register.py
    └── reset_password.py
```

This is optional — only useful when an endpoint's logic spans 30+ LOC
of plumbing. Don't add it for simple CRUD.

### Add `listeners.py` when

You need to react to domain events from elsewhere. See
[events.md](events.md). Import the module once in `__init__.py` so
handlers register at boot:

```python
# modules/ops/audit/__init__.py
from app.modules.ops.audit import listeners  # noqa: F401
```

## Naming

- `router.py` (singular), not `routes.py`.
- `service.py` (singular), not `services.py`. If you split into a
  folder, the folder is also `service/`.
- Models live in `app/models/<entity>.py`, not in the module — the
  flat layout lets alembic's `env.py` find them.
- Event classes: past tense (`WorkspaceCreated`, not `CreateWorkspace`).

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| `routes.py`, `services.py` | `router.py`, `service.py` |
| SQL in routers | Service helper functions |
| Inline `audit.log_event(...)` everywhere | Emit a domain event, audit listens |
| Threading `user_id` through every signature | Read `current_user_id()` |
| Splitting `service.py` by line count | Split by aggregate boundary |
| New top-level bucket under `modules/` | Find which of the 7 fits |

## Adding a new feature: checklist

1. Pick the bucket (or argue for placing it in `studio` — usually the
   right answer for new user-facing primitives).
2. Create the canonical folder shape (router/service/schemas).
3. Add SQLAlchemy model under `app/models/` and register in
   `app/models/__init__.py`.
4. Generate alembic migration.
5. Wire the router into `app/main.py`.
6. Decide: does this feature need to **announce** events for others
   to react? Define them in `events/types.py` or module-local.
7. Tests under `tests/<feature>_*.py` — start with service-level unit
   tests, layer router/integration tests as endpoints stabilise.
