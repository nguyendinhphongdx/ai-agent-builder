---
id: arch-phase-1-progress
title: Phase 1 Progress Log — Multi-tenancy Rollout Status
domain: architecture
tags: [progress, status, multi-tenancy, workspace, organization, phase-1, rollout, log, session-handoff, agent-handoff]
related: [arch-enterprise-roadmap, arch-system-overview, arch-operations]
summary: Live status of the Phase 1.1 multi-tenancy rollout. Tracks which migrations, models, services, and tests are done, which are pending, what decisions have been made, and where the next session should resume. Read this BEFORE re-reading the full roadmap when picking up the project — it's the single source of truth for progress.
---

# Phase 1 Progress Log

> **Audience**: future Claude / Codex sessions, or any engineer joining after a pause.
> **Read order**: this file first, then [arch-enterprise-roadmap](./enterprise-roadmap.md) for the full plan, then dive into code.
> **Maintenance rule**: update this file at the END of every working session. The summary section + "Resume from here" must be accurate before signing off.

---

## ⏱ Current Snapshot

- **Last updated**: 2026-05-11
- **Phase**: 1.1 — Multi-tenancy foundation
- **Step**: 1 ✅ (schema additive) · 2 🟡 (proof-of-pattern done for agents only) · 3 ⏳ pending · 4 ⏳ pending
- **Active branch**: `master` (no feature branch yet)
- **Blocking decision waiting on user**: backfill strategy (data migration vs CLI script) — see [Open Decisions](#-open-decisions-awaiting-user) below.

---

## ▶ Resume from here (next session quick start)

If you're picking this up cold, do this in order:

1. **Verify the existing work runs** (assumes Docker + Python 3.12 installed):
   ```bash
   cd apps/backend
   pip install -e ".[dev]"
   pytest -m "not integration" -v       # must still pass — regression check
   pytest -m integration -v             # needs Docker; spins up Postgres testcontainer
   ```
   Failure here = **stop and investigate before adding more**. Likely culprits: alembic chain typo, missing __init__.py, circular import on `app.workspaces.service`.

2. **Wait for user decision on**: backfill strategy + whether to scale step-2 pattern to remaining tables now or build the workspace API first. Both options are listed in [Open Decisions](#-open-decisions-awaiting-user).

3. **If user says "go": next concrete tasks** in priority order:
   - **a.** Backfill migration (Phase 1.1 step 3) for existing users + their resources. Single alembic data migration that creates a personal Org+Workspace+Member per user and stamps `agents.workspace_id` from `users.default_workspace_id`.
   - **b.** Apply step-2 pattern to next group: ai_credentials + personal_access_tokens (auth/credentials cluster — small blast radius, similar shape to agents).
   - **c.** Then group 2: tools + knowledge_bases + documents + document_chunks + conversations.
   - **d.** Then group 3: workflows + workflow_nodes + workflow_edges + workflow_runs.
   - **e.** Finally, step 4: ALTER `workspace_id SET NOT NULL` across every table — only after backfill verified clean on staging.

---

## ✅ Done

### Test infrastructure (Phase 0)

| File | Purpose |
|---|---|
| [pyproject.toml](../../apps/backend/pyproject.toml) | Added `testcontainers[postgres]>=4.8` + `factory-boy>=3.3` to `[dev]` extras |
| [tests/integration/__init__.py](../../apps/backend/tests/integration/__init__.py) | Marker package |
| [tests/integration/conftest.py](../../apps/backend/tests/integration/conftest.py) | Postgres container fixture (session-scoped) + alembic upgrade head + per-test transaction rollback. Auto-tags every test in this folder with `integration` marker. |
| [tests/integration/test_smoke.py](../../apps/backend/tests/integration/test_smoke.py) | Validates the fixture pipeline end-to-end |
| [tests/factories/__init__.py](../../apps/backend/tests/factories/__init__.py) | Factory exports + `create()` helper that adds-and-flushes |
| [tests/factories/users.py](../../apps/backend/tests/factories/users.py) | UserFactory |
| [tests/factories/workspaces.py](../../apps/backend/tests/factories/workspaces.py) | OrganizationFactory, WorkspaceFactory, WorkspaceMemberFactory, WorkspaceInvitationFactory |

**Pre-existing CI**: [`.github/workflows/backend.yml`](../../.github/workflows/backend.yml) already runs ruff + pytest unit-only. Frontend CI also already exists. We did NOT add mypy/coverage/migration-check to CI yet — defer to Phase 0.1 when Phase 1.1 lands.

### Phase 1.1 step 1 — Multi-tenancy schema (additive)

**Migrations chain**: `l1b3c9e7d5f2` (existing) → `m2c4d8e1f3a5` → `n3d5e9f2a4b6` → `o4e6f0a3b5c7`

| Migration | What it does |
|---|---|
| [m2c4d8e1f3a5_organizations_workspaces.py](../../apps/backend/alembic/versions/m2c4d8e1f3a5_organizations_workspaces.py) | Creates `organizations`, `workspaces`, `workspace_members`, `workspace_invitations`. Touches no existing tables. Fully reversible. |
| [n3d5e9f2a4b6_users_default_workspace_id.py](../../apps/backend/alembic/versions/n3d5e9f2a4b6_users_default_workspace_id.py) | Adds `users.default_workspace_id` (nullable FK → workspaces, ON DELETE SET NULL) + index |
| [o4e6f0a3b5c7_agents_workspace_id.py](../../apps/backend/alembic/versions/o4e6f0a3b5c7_agents_workspace_id.py) | Adds `agents.workspace_id` (nullable FK → workspaces, ON DELETE CASCADE) + index. **Step 2 proof of pattern.** |

**New models**:
- [organization.py](../../apps/backend/app/models/organization.py) — plan tier constants `ORG_PLAN_FREE/STARTER/PRO/ENTERPRISE`, `settings` JSONB for branding
- [workspace.py](../../apps/backend/app/models/workspace.py) — slug unique per-org, `is_personal` flag for the auto-created one
- [workspace_member.py](../../apps/backend/app/models/workspace_member.py) — composite PK `(workspace_id, user_id)`, role constants `WORKSPACE_ROLE_VIEWER/EDITOR/ADMIN/OWNER`
- [workspace_invitation.py](../../apps/backend/app/models/workspace_invitation.py) — opaque `token`, `expires_at`, `accepted_at`

**Modified models**:
- [user.py](../../apps/backend/app/models/user.py) — added `default_workspace_id` column + `default_workspace` relationship (eager-joined)
- [agent.py](../../apps/backend/app/models/agent.py) — added `workspace_id` column + `workspace` relationship
- [models/__init__.py](../../apps/backend/app/models/__init__.py) — exported the 4 new models

### Phase 1.1 step 2 (PARTIAL) — Service layer plumbing

| File | What changed |
|---|---|
| [app/workspaces/service.py](../../apps/backend/app/workspaces/service.py) | NEW. `ensure_personal_workspace(db, user)` is idempotent: fast-path on `default_workspace_id` set, recovery path if pointer null but Org exists, full create otherwise. `list_user_workspace_ids(db, user_id)` for tenant-scoped queries. Slug derivation: `user-{uuid_hex[:8]}`. |
| [app/context.py](../../apps/backend/app/context.py) | Added `_current_workspace_id` ContextVar + `set_current_workspace_id` / `reset_current_workspace_id` / `current_workspace_id_or_none` helpers. Plus `run_in_request_context_with_workspace` for background tasks that need to inherit tenancy. |
| [app/auth/dependencies.py](../../apps/backend/app/auth/dependencies.py) | `get_current_user` now also reads `X-Workspace-Id` header → falls back to `user.default_workspace_id` → seeds the ContextVar. Bad header values silently fall through (same forgiveness as Accept-Language). |
| [app/auth/service.py](../../apps/backend/app/auth/service.py) | `create_user` got a `provision_workspace=True` kwarg that calls `ensure_personal_workspace` after the flush. CLI scripts can opt out by passing `False`. |
| [app/auth/oauth_router.py](../../apps/backend/app/auth/oauth_router.py) | Fresh OAuth signups (`_match_or_create_user`) now also call `ensure_personal_workspace` after the user row is flushed. |
| [app/cli/seed_admin.py](../../apps/backend/app/cli/seed_admin.py) | Admin bootstrap now also gets a personal workspace — admin role and tenancy are orthogonal. |
| [app/agents/service.py](../../apps/backend/app/agents/service.py) | `create_agent` auto-fills `workspace_id` from ContextVar. `list_agents` / `get_agent` filter `workspace_id = current OR workspace_id IS NULL` (legacy-friendly during transition). |

**Login endpoint** ([app/auth/router.py](../../apps/backend/app/auth/router.py)) — **DOES NOT** call `ensure_personal_workspace`. An earlier draft did; the user reverted that edit because login is a hot path and existing-user healing belongs in the backfill migration instead. Keep it that way unless explicitly asked.

### Integration tests

| File | What it covers |
|---|---|
| [test_workspaces.py](../../apps/backend/tests/integration/test_workspaces.py) | 7 tests: org/workspace creation, slug uniqueness per-org, composite PK on members, invitation token uniqueness, cascade-delete via org, SET NULL on inviter delete, relationship eager-load, UUID type enforcement |
| [test_ensure_personal_workspace.py](../../apps/backend/tests/integration/test_ensure_personal_workspace.py) | 6 tests: full creation, idempotency, recovery from null pointer, fallback name when no full_name, list_user_workspace_ids, two users get distinct orgs |
| [test_agent_workspace_isolation.py](../../apps/backend/tests/integration/test_agent_workspace_isolation.py) | 5 tests: auto-fill workspace_id on create, list isolation, get cross-workspace blocked, legacy NULL rows still visible during transition, no-context fallback |

**Verification status**: ⚠️ NOT yet run on a real machine — the dev environment used to author this didn't have Python or Docker installed. The user will run them on their dev machine. If anything fails, fix before resuming step-2 rollout.

---

## 🟡 In progress / paused mid-flight

Nothing actively in flight — clean handoff at a natural pause point. Step 2 is "1 of 12 tables done"; the remaining 11 are queued behind a user decision.

---

## ⏳ Pending — Phase 1.1 remaining

| Step | Description | Blocked by |
|---|---|---|
| **2 (rest)** | Add `workspace_id` to `tools`, `knowledge_bases`, `documents`, `document_chunks`, `conversations`, `messages`, `workflows`, `workflow_nodes`, `workflow_edges`, `workflow_runs`, `ai_credentials`, `personal_access_tokens` — and update each module's service layer to mirror the agents pattern. Group as 3 PRs (auth/creds → AI resources → workflows) per user choice. | User confirms agents pattern is OK |
| **3 — Backfill** | Data migration (or CLI script — TBD) that, for every existing user without `default_workspace_id`: creates personal Org+Workspace+Member, stamps `users.default_workspace_id`, then UPDATEs every resource table's `workspace_id` from the row's `user_id` → that user's personal workspace. | Strategy decision (see Open Decisions) |
| **4 — Lock** | `ALTER COLUMN workspace_id SET NOT NULL` on every resource table. Single migration, runs only on green staging after backfill. | Step 3 done, staging soak |

---

## 🔧 Decisions made (with rationale)

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-10 | 2-layer tenancy: `Organization` parent + `Workspace` child | Slack Enterprise Grid / Atlassian Cloud pattern. Lets one paying customer have many workspaces under one billing relationship + one SSO config. Cost is ~10-15% extra schema complexity now to avoid migrating away from a single-layer design later. |
| 2026-05-10 | Slug-as-uuid-prefix for personal Orgs (`user-<8hex>`) | Avoids slug collision logic (email and full_name aren't unique). Trades human readability of the slug for guaranteed uniqueness without retry loops. |
| 2026-05-10 | `default_workspace_id` on User instead of always-derive-from-membership | UX shortcut: login lands user on last-used workspace without an extra round-trip. Set on signup, updated by switcher. Falls back to first membership if null. |
| 2026-05-11 | Login does NOT auto-call `ensure_personal_workspace` | Login is a hot path — adding 3-4 queries per request to handle a one-time legacy-user heal is the wrong tradeoff. Backfill migration handles existing users at deploy time. |
| 2026-05-11 | Service queries during transition use dual filter `WHERE user_id = X AND (workspace_id = Y OR workspace_id IS NULL)` | Legacy rows (workspace_id NULL) keep working; new rows are tenant-scoped. Once backfill stamps every row and column flips to NOT NULL, the OR-NULL branch is removed. |
| 2026-05-11 | Migration approach: 3 PRs by group, not big-bang | Smaller blast radius, easier review, each PR independently rollback-safe. |

---

## ❓ Open decisions awaiting user

1. **Backfill strategy** — pick one before starting step 3:
   - **A. Alembic data migration** runs as part of `alembic upgrade head`. Pros: deploy-time atomic, ops doesn't need to remember a second step. Cons: long migration on big tables blocks deploy.
   - **B. Standalone CLI script** (`python -m app.cli.backfill_tenancy`). Pros: ops controls timing, can run in batches with progress reporting. Cons: extra step, easy to forget.
   - **C. Hybrid**: alembic migration that adds the columns, CLI script that backfills. (This is essentially what we have already — column adds are migrations, backfill is the missing CLI.)

2. **Workspace CRUD API timing** — build `/api/workspaces/` endpoints (create, list, invite, accept, leave, delete) NOW alongside step-2 rollout, or AFTER all tables are migrated? Frontend cannot show a workspace switcher until these exist.

3. **Pattern review**: is the dual-filter SELECT (`user_id = X AND (workspace_id = Y OR IS NULL)`) acceptable for the transition window, or would you rather we do all-tables-at-once + immediate `NOT NULL` to avoid the legacy branch entirely? (Latter is more invasive but has cleaner end state.)

---

## 📋 Files touched in Phase 1.1 so far

**New (18)**:
```
apps/backend/alembic/versions/m2c4d8e1f3a5_organizations_workspaces.py
apps/backend/alembic/versions/n3d5e9f2a4b6_users_default_workspace_id.py
apps/backend/alembic/versions/o4e6f0a3b5c7_agents_workspace_id.py
apps/backend/app/models/organization.py
apps/backend/app/models/workspace.py
apps/backend/app/models/workspace_member.py
apps/backend/app/models/workspace_invitation.py
apps/backend/app/workspaces/__init__.py
apps/backend/app/workspaces/service.py
apps/backend/tests/factories/__init__.py
apps/backend/tests/factories/users.py
apps/backend/tests/factories/workspaces.py
apps/backend/tests/integration/__init__.py
apps/backend/tests/integration/conftest.py
apps/backend/tests/integration/test_smoke.py
apps/backend/tests/integration/test_workspaces.py
apps/backend/tests/integration/test_ensure_personal_workspace.py
apps/backend/tests/integration/test_agent_workspace_isolation.py
```

**Modified (10)**:
```
apps/backend/pyproject.toml
apps/backend/app/models/__init__.py
apps/backend/app/models/user.py
apps/backend/app/models/agent.py
apps/backend/app/context.py
apps/backend/app/auth/service.py
apps/backend/app/auth/oauth_router.py
apps/backend/app/auth/dependencies.py
apps/backend/app/cli/seed_admin.py
apps/backend/app/agents/service.py
```

**NOT modified (intentional)**:
```
apps/backend/app/auth/router.py    # login hot path — backfill handles legacy users
```

---

## 🧠 Mental model for future agents

The transition strategy is **"add column nullable → backfill → enforce NOT NULL"**, repeated table-by-table. At any commit on master the system must remain runnable: legacy single-tenant code paths keep working until backfill is verified. That's why every step is reversible and additive.

The two ContextVars (`current_user_id` + `current_workspace_id`) are the spine of tenant scoping. Services NEVER pass `user_id` / `workspace_id` as positional args — they read from the ContextVar. Background tasks that need to inherit must use `run_in_request_context_with_workspace`. Any service that bypasses this is a tenancy bug.

Personal workspaces are not special infrastructure — they're regular Org+Workspace rows with `is_personal=True`. The flag only changes UI presentation (hide team-management features) and billing (always Free plan, capped resources). All other code paths treat them like any other workspace.

---

## 📚 Cross-references

- [arch-enterprise-roadmap](./enterprise-roadmap.md) — full 12-month plan, Phase 1.1 spec lives there
- [arch-system-overview](./system-overview.md) — current system architecture (pre-multi-tenancy diagrams; update after Phase 1.1 lands)
- [arch-operations](./operations.md) — ops runbook (will be expanded by Phase 1.2 queue work + 2.2 observability)
