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

- **Last updated**: 2026-05-11 (session 2)
- **Phase**: 1.1 — Multi-tenancy foundation
- **Step**: 1 ✅ schema · 2 ✅ all 13 tables stamped · 3 ✅ CLI built · 4 ✅ lock migration shipped — must run AFTER backfill on staging.

**Phase 1.1 is feature-complete.** What's left is ops: run `python -m app.cli.backfill_tenancy` then `alembic upgrade head` on staging, smoke test, deploy to prod.
- **Workspace API**: ✅ Block 1 CRUD + members + invitations shipped (decided NOW path)
- **Open decisions** (closed in session 2):
  - **Backfill strategy**: **(C) Hybrid** — alembic adds columns (already done), CLI script does the data backfill
  - **Workspace API timing**: **NOW**, parallel to step-2 rollout (Block 1 done)
  - **Pattern**: keep **dual-filter** for transition; collapse on step 4
- **Active branch**: `master`

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

2. **Decisions are locked** (see Current Snapshot). Next concrete blocks in execution order:
   - **Block 2** — Frontend workspace switcher (header Combobox) + `/settings/workspace` page (members + invitations + danger zone). Unblocks dogfood.
   - **Block 3** — Step-2 Group A: add `workspace_id` to `ai_credentials` + `personal_access_tokens`. Mirror agents pattern.
   - **Block 4** — Step-2 Group B: tools + knowledge_bases + documents + document_chunks + conversations + messages.
   - **Block 5** — Step-2 Group C: workflows + workflow_nodes + workflow_edges + workflow_runs.
   - **Block 6** — `python -m app.cli.backfill_tenancy` script. Run on staging.
   - **Block 7** — Lock `workspace_id SET NOT NULL` everywhere; remove dual-filter OR-NULL branches in services.
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
| [test_workspaces_api.py](../../apps/backend/tests/integration/test_workspaces_api.py) | 16 tests covering Block 1 service layer: create_team_workspace (fresh org / attach existing / slug retry), list_user_workspaces with role, update + delete (refuse personal), member promote/demote/remove with last-owner guard, invitation create/accept/expire/used/idempotent re-accept, role_at_least helper. |

**Verification status**: ⚠️ NOT yet run on a real machine — author had no Docker. User will run them; if anything fails, fix before resuming step-2 rollout.

### Phase 1.1 — Block 1 Workspace CRUD API (session 2)

| File | What it does |
|---|---|
| [app/workspaces/service.py](../../apps/backend/app/workspaces/service.py) | Extended with `list_user_workspaces` (paired with role), `create_team_workspace` (fresh org or attach), `update_workspace`, `delete_workspace` (refuses personal), member helpers (`list_members`, `get_member`, `update_member_role`, `remove_member`) with last-owner guards, and invitation helpers (`create_invitation`, `list_invitations`, `revoke_invitation`, `get_invitation_by_token` rejecting expired/used, idempotent `accept_invitation`). |
| [app/workspaces/schemas.py](../../apps/backend/app/workspaces/schemas.py) | NEW. Pydantic shapes: `WorkspaceSummary` (with caller role + embedded org), `WorkspaceCreate/Update`, `MemberResponse` (eager user), `InvitationCreate/Response/AcceptResponse`. |
| [app/workspaces/permissions.py](../../apps/backend/app/workspaces/permissions.py) | NEW. `require_workspace_role(min_role)` dep — resolves `workspace_id` path param via FastAPI sub-dep injection, fetches the caller's `WorkspaceMember`, 404 if not member, 403 if role rank below min. Returns the member row. Plus `role_at_least(role, min)` rank helper. |
| [app/workspaces/router.py](../../apps/backend/app/workspaces/router.py) | NEW. 11 endpoints under `/api/workspaces`: list/create/get/patch/delete workspace, list/patch/remove members (self-leave allowed), list/create/revoke invitations, public `POST /workspaces/invitations/{token}/accept`. Role gates: viewer for reads, admin for membership/invitation mgmt, owner for delete + grant-owner. |
| [app/main.py](../../apps/backend/app/main.py) | Wires `workspaces_router`. |

### Phase 1.1 — Block 2 Frontend switcher + settings (session 2)

| File | What it does |
|---|---|
| [features/workspaces/types/index.ts](../../apps/frontend/src/features/workspaces/types/index.ts) | NEW. TS shapes mirroring backend schemas + `roleAtLeast` helper. |
| [lib/api/workspaceService.ts](../../apps/frontend/src/lib/api/workspaceService.ts) | NEW. Wraps all 11 endpoints. |
| [features/workspaces/stores/workspaceStore.ts](../../apps/frontend/src/features/workspaces/stores/workspaceStore.ts) | NEW. Zustand + persist middleware (`agentforge:current-workspace` key) holding `currentWorkspaceId`. |
| [lib/api/client.ts](../../apps/frontend/src/lib/api/client.ts) | Request interceptor injects `X-Workspace-Id` from persisted store via raw localStorage (SSR-safe). |
| [features/workspaces/hooks/useWorkspaces.ts](../../apps/frontend/src/features/workspaces/hooks/useWorkspaces.ts) | NEW. TanStack Query + mutation hooks; auto-selects personal workspace on first load; invalidates query keys on every mutation. |
| [features/workspaces/components/WorkspaceSwitcher.tsx](../../apps/frontend/src/features/workspaces/components/WorkspaceSwitcher.tsx) | NEW. Header dropdown — switching invalidates *every* cached query. |
| [features/workspaces/components/CreateWorkspaceDialog.tsx](../../apps/frontend/src/features/workspaces/components/CreateWorkspaceDialog.tsx) | NEW. Single-field create modal. |
| [features/workspaces/views/WorkspaceSettingsView.tsx](../../apps/frontend/src/features/workspaces/views/WorkspaceSettingsView.tsx) | NEW. Tabs: Members / Invitations / General / Danger zone. Personal workspaces short-circuit to "can't manage" notice. Invite flow auto-copies accept URL to clipboard. |
| [features/workspaces/views/AcceptInvitationView.tsx](../../apps/frontend/src/features/workspaces/views/AcceptInvitationView.tsx) | NEW. Auto-fires accept mutation; success/fail states with redirect to `/home`. |
| [components/layout/Header.tsx](../../apps/frontend/src/components/layout/Header.tsx) | Mounts `<WorkspaceSwitcher />`. |
| [features/settings/components/SettingsNav.tsx](../../apps/frontend/src/features/settings/components/SettingsNav.tsx) | Adds "Workspace" entry in the Workspace group. |
| [app/(dashboard)/settings/workspace/page.tsx](../../apps/frontend/src/app/(dashboard)/settings/workspace/page.tsx) | NEW route. |
| [app/(dashboard)/workspaces/invitations/[token]/page.tsx](../../apps/frontend/src/app/(dashboard)/workspaces/invitations/[token]/page.tsx) | NEW route — `params` is a `Promise` (Next 16). |

### Phase 1.1 — Block 7 Lock NOT NULL + dual-filter cleanup (session 2)

Closes Phase 1.1 step 4. Code lands here; deploy is gated on backfill running to completion on staging.

| File | What changed |
|---|---|
| [alembic/versions/s8i1j4e7f9g2_lock_workspace_id_not_null.py](../../apps/backend/alembic/versions/s8i1j4e7f9g2_lock_workspace_id_not_null.py) | NEW migration. `ALTER COLUMN workspace_id SET NOT NULL` across all 13 resource tables. If any NULL row remains the ALTER aborts and the migration rolls back. `users.default_workspace_id` stays NULLABLE on purpose (its FK is `ON DELETE SET NULL`). |
| All 13 resource models | `Mapped[uuid.UUID \| None]` → `Mapped[uuid.UUID]`, `nullable=True` → `nullable=False`. Comments updated to reflect the post-lock contract. |
| Services (agents, ai_credentials, personal_access_tokens, tools, knowledge_bases, conversations, workflows) | `_scope_filter` collapsed from `WHERE workspace_id = X OR IS NULL` to strict `WHERE workspace_id = X`. The `current_workspace_id_or_none` no-context branch stays (background tasks, CLI). |
| Tests | `test_legacy_null_rows_visible_during_transition` flipped to `test_legacy_null_rows_are_invisible_after_lock` for both agents and credentials — strict filter is the new contract. |

**Deploy sequence (mandatory order):**

1. `python -m app.cli.backfill_tenancy --dry-run` — verify counts make sense.
2. `python -m app.cli.backfill_tenancy` — actually backfill.
3. `python -m app.cli.backfill_tenancy --dry-run` again — must report 0 across every table.
4. `alembic upgrade head` — the lock migration runs. If it fails on any table, repeat steps 2-3.
5. Deploy this code. Services are already using the strict filter; they just need the NOT NULL DB state for the assumption to hold.

If you deploy this code BEFORE the migration runs, any user whose `default_workspace_id` is still NULL will see no rows on workspace-scoped queries — the auth dep sets the context to NULL, and the strict filter drops everything in that case (intentional — we don't want implicit cross-tenant leaks).

### Phase 1.1 — Block 6 Backfill CLI (session 2)

`python -m app.cli.backfill_tenancy` — two-phase rollout for legacy rows. Idempotent + dry-run capable + batched for low lock contention.

| File | What it does |
|---|---|
| [app/cli/backfill_tenancy.py](../../apps/backend/app/cli/backfill_tenancy.py) | NEW. **Phase A**: streams `User` rows with `default_workspace_id IS NULL`, calls `ensure_personal_workspace` per user. **Phase B**: stamps `workspace_id` on every resource table — direct via `users.default_workspace_id` (7 tables with `user_id`) or via parent FK (6 child tables: documents/chunks/messages/workflow_nodes/edges/runs). Uses `WITH targets AS (… LIMIT :batch) UPDATE … FROM targets` so a 50M-row backfill doesn't lock the whole table. Loop exits when batch returns 0 rows. |
| [tests/integration/test_backfill_tenancy.py](../../apps/backend/tests/integration/test_backfill_tenancy.py) | 4 smoke tests: Phase A provisions personal workspaces; dry-run leaves DB untouched; Phase B stamps legacy NULL rows (agents + KB); idempotent re-run reports zero updates on green DB. |

**Operational notes** for the user to run:

```bash
# 1. Dry-run first to see what's affected.
python -m app.cli.backfill_tenancy --dry-run

# 2. Run Phase A alone (small, safe).
python -m app.cli.backfill_tenancy --users-only

# 3. Run Phase B with larger batch on quiet hours.
python -m app.cli.backfill_tenancy --resources-only --batch-size 10000

# 4. Confirm clean — second run should report 0 updates everywhere.
python -m app.cli.backfill_tenancy
```

Only after the second run reports 0 across every table can Block 7's lock migration safely run.

### Phase 1.1 — Block 5 Step-2 Group C (session 2)

`workspace_id` added to **workflows**, **workflow_nodes**, **workflow_edges**, **workflow_runs**. Step-2 is now closed — all 13 resource tables stamped.

| File | What changed |
|---|---|
| [alembic/versions/r7h9i3d6e8f0_workflows_workspace_id.py](../../apps/backend/alembic/versions/r7h9i3d6e8f0_workflows_workspace_id.py) | NEW migration. 4 ALTER TABLEs in one revision, same nullable-FK-CASCADE pattern. |
| [app/models/workflow.py](../../apps/backend/app/models/workflow.py), [workflow_node.py](../../apps/backend/app/models/workflow_node.py), [workflow_edge.py](../../apps/backend/app/models/workflow_edge.py), [workflow_run.py](../../apps/backend/app/models/workflow_run.py) | `workspace_id` column added on each. Child tables denormalise from parent workflow. |
| [app/workflows/service.py](../../apps/backend/app/workflows/service.py) | `list_workflows`/`get_workflow` use dual-filter `_scope_filter`; `create_workflow` auto-fills from ContextVar; `save_workflow_graph` propagates `workspace_id` to every node + edge insert; `create_workflow_run` inherits from parent workflow via single scalar lookup. |

### Phase 1.1 — Block 4 Step-2 Group B (session 2)

`workspace_id` added to **tools**, **knowledge_bases**, **documents**, **document_chunks**, **conversations**, **messages**.

| File | What changed |
|---|---|
| [alembic/versions/q6g8h2c5d7e9_resources_workspace_id.py](../../apps/backend/alembic/versions/q6g8h2c5d7e9_resources_workspace_id.py) | NEW migration. One file, 6 ALTER TABLEs — same nullable-FK-CASCADE shape as agents. |
| Models: [tool.py](../../apps/backend/app/models/tool.py), [knowledge_base.py](../../apps/backend/app/models/knowledge_base.py), [document.py](../../apps/backend/app/models/document.py), [document_chunk.py](../../apps/backend/app/models/document_chunk.py), [conversation.py](../../apps/backend/app/models/conversation.py), [message.py](../../apps/backend/app/models/message.py) | `workspace_id` column added on each. Child tables (documents, chunks, messages) denormalise from parent for fast scan-free filtering on hot paths (RAG retrieval, cost dashboards). |
| [app/tools/service.py](../../apps/backend/app/tools/service.py) | Dual-filter `_scope_filter` on list/get; `create_tool` auto-fills from ContextVar. |
| [app/knowledge/service.py](../../apps/backend/app/knowledge/service.py) | Same on `list_knowledge_bases`/`get_knowledge_base`/`create_knowledge_base`. `get_knowledge_base_unscoped` left as-is for trusted background jobs. |
| [app/knowledge/router.py](../../apps/backend/app/knowledge/router.py) | Document insert inherits `workspace_id` from parent KB. |
| [app/knowledge/ingestion.py](../../apps/backend/app/knowledge/ingestion.py) | DocumentChunk creation inherits `workspace_id` from KB so embeddings are tenant-tagged. |
| [app/conversations/service.py](../../apps/backend/app/conversations/service.py) | Dual-filter on list/get; `create_conversation` pins `workspace_id` from the **agent's** workspace (anonymous share-channel conversations must follow the agent, not the caller). `save_message` denormalises from parent conversation. |

### Phase 1.1 — Block 3 Step-2 Group A (session 2)

`workspace_id` added to **ai_credentials** + **personal_access_tokens** mirroring the agents proof-of-pattern.

| File | What changed |
|---|---|
| [alembic/versions/p5f7g1b4c6d8_creds_tokens_workspace_id.py](../../apps/backend/alembic/versions/p5f7g1b4c6d8_creds_tokens_workspace_id.py) | NEW migration. Adds nullable FK + index on both tables. Reversible. |
| [app/models/ai_credential.py](../../apps/backend/app/models/ai_credential.py) | New `workspace_id` column, indexed, FK CASCADE → workspaces. |
| [app/models/personal_access_token.py](../../apps/backend/app/models/personal_access_token.py) | Same. Tokens carry their own tenant binding so `/external/*` calls scope correctly regardless of caller's header. |
| [app/ai_credentials/service.py](../../apps/backend/app/ai_credentials/service.py) | `create_ai_credential` auto-fills from context; list/get/update/delete use dual-filter `_scope_filter`. `get_plaintext_key_by_id` (runtime executor lookup) intentionally NOT scoped — agents store `credential_id` directly. |
| [app/personal_tokens/service.py](../../apps/backend/app/personal_tokens/service.py) | Same dual-filter pattern; `create_token` stamps `workspace_id`. |
| [app/personal_tokens/schemas.py](../../apps/backend/app/personal_tokens/schemas.py) | `TokenResponse` now exposes `workspace_id`. |
| [app/auth/dependencies.py](../../apps/backend/app/auth/dependencies.py) | API-token branch: workspace context comes from `token.workspace_id` (NOT header) so external calls always scope to where the token was minted. Legacy tokens with NULL fall back to `user.default_workspace_id`. |
| [tests/integration/test_creds_tokens_workspace_isolation.py](../../apps/backend/tests/integration/test_creds_tokens_workspace_isolation.py) | 7 tests covering auto-fill, list isolation across workspaces, legacy NULL row visibility, cross-workspace `get`/`revoke` returns None. |

---

## 🟡 In progress / paused mid-flight

Nothing actively in flight — clean handoff at a natural pause point. Step 2 is "3 of 12 tables done"; remaining groups B (6 tables) and C (4 tables) follow the same pattern.

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
