---
id: arch-hub-auth-refactor
title: Hub + workspace-in-token refactor
domain: architecture
tags: [auth, multi-tenancy, workspace, organization, jwt, hub, refactor]
related: [arch-system-overview, arch-deployment, arch-operations]
summary: Two-stage auth model — user_token gates the Org Hub, workspace_token binds a session to one workspace. Replaces localStorage workspace state.
---

# Hub + workspace-in-token refactor

## Motivation

Today the **workspace context** of every request is derived from a
client-controlled value: the `X-Workspace-Id` header, hydrated from
`localStorage["agentforge:current-workspace"]` by an axios interceptor.
That has three real problems:

1. **localStorage is editable.** A user opening DevTools and typing a
   workspace UUID they aren't a member of forces every subsequent
   request to claim that tenant. Backend permission checks reject the
   query, but the *audit log records the attempt* against the wrong
   tenant and the FE behaves oddly until a 403 surfaces.
2. **Token + tenant are decoupled.** A request's tenant cannot be
   trusted from the token alone — the BE must re-join through
   `workspace_members` on every call. Tens of millions of
   small-but-redundant queries.
3. **No "org home"**. Login lands the user inside their personal
   workspace; org-level surfaces (workspace list, member management,
   billing, security, audit) have nowhere natural to live. The
   existing `/settings/workspace` tab is a hack that lets workspace
   admins set their *own* caps.

The fix copies a pattern that Slack / Notion / Linear all use: a
**two-stage auth model**.

## Token model

```
Stage 1 — user_token (after login)
─────────────────────────────────
cookie: access_token         ← unchanged name for back-compat
payload:
  { sub: user_id
  , type: "user"
  , exp: ... }

  Reaches: /api/auth/me, /api/organizations/*,
           /api/billing/*, /hub/* (FE)

  Cannot reach: /api/workspaces/{id}/*, /api/agents/*,
                /api/conversations/*, /api/knowledge-bases/*,
                /api/workflows/*  — anything tenant-scoped.

Stage 2 — workspace_token (after pick)
──────────────────────────────────────
cookie: access_token         ← replaces user_token in the same slot
payload:
  { sub: user_id
  , type: "workspace"
  , ws: workspace_id
  , org: organization_id
  , exp: ... }

  Reaches: everything user_token reaches PLUS
           every tenant-scoped route.
```

Cookies use the same name so the FE doesn't need two stores. The
discriminator is `type`. Refresh tokens stay one shape — refresh
returns a token of whatever type was active.

## Routes

```
/login                       login form
/register                    signup form
/hub                         org-level landing (PHASE 1+)
   /hub/workspaces           list, create, delete, quota cap
   /hub/members              org members (invite, role, remove)
   /hub/billing              plan, invoices, payment method
   /hub/security             SSO, SCIM, IP allowlist
   /hub/audit                org-level audit log
   /hub/settings             org name, billing email, branding
/app/{ws-slug}               workspace-scoped dashboard (PHASE 2+)
   /app/{ws-slug}/home
   /app/{ws-slug}/agents
   /app/{ws-slug}/chat
   /app/{ws-slug}/knowledge
   /app/{ws-slug}/workflows
   /app/{ws-slug}/tools
   /app/{ws-slug}/settings   workspace-level settings (members,
                              rename, danger zone — NO quota tab)
```

URL `{ws-slug}` is presentational only — the workspace_token in the
cookie is the security boundary. The slug in the URL must match the
token's `ws` claim or the request 403s.

## New endpoints

```
POST /api/auth/enter-workspace        { workspace_id }
  Body: workspace id user wants to enter.
  Auth: requires a user_token (or any token).
  Side effects:
    1. Verify user is a member (or effective member via org role).
    2. Mint a workspace_token; replace the access_token cookie.
    3. Return { workspace, organization } so FE can update state +
       route to /app/{slug}.

POST /api/auth/exit-workspace
  No body. Replaces access_token with a fresh user_token.
  Used by "Back to Hub" affordance.

GET  /api/auth/me
  Already exists; gains a {token_type} field so the FE can route
  to /hub vs /app/* without an extra round-trip.

GET  /api/organizations/{org_id}/workspaces
  Lists every workspace under one org — org-admins who never joined
  a workspace personally can still enumerate + manage them.
  Auth: ORG_SETTINGS_READ.

  Today /api/workspaces only lists workspaces the caller is a
  member of (workspace_members join).
```

## Switching workspace (Linear-style)

Switcher dropdown items call `POST /api/auth/enter-workspace` on
click — BE mints new token, FE swaps `router.push` to
`/app/{new-slug}/home`. No round-trip through Hub.

The "Back to Hub" button issues `POST /api/auth/exit-workspace` then
`router.push("/hub")`.

## Migration phases

Each phase is a coherent ship-able commit. The application keeps
working at every boundary — no half-built state.

### Phase 0 — additive BE foundation
- Add `type` discriminator to `access_token` payload (always emit;
  old clients ignore it).
- Add `ws` / `org` claims, optional, set only on workspace_token.
- Implement POST /api/auth/enter-workspace + /exit-workspace.
- Implement GET /api/organizations/{org_id}/workspaces.
- `get_current_user`: read `ws` from claim first, fall back to
  `X-Workspace-Id` header (back-compat).
- No FE change yet.

### Phase 1 — Hub UI (workspaces tab only)
- `/hub` layout with sidebar nav.
- `/hub/workspaces` — list + create + delete + per-row quota cap
  edit (the quota cap UI moves from workspace-settings here).
- Workspace-settings Quota tab → read-only banner pointing at
  `/hub/workspaces`.
- WorkspaceSwitcher refactor:
  - dropdown items: `enter-workspace` → push `/app/{slug}/home`
  - "Manage in Hub" link → push `/hub/workspaces`

### Phase 2 — Route refactor
- New routes under `/app/{ws-slug}/*` — alias to current
  `(dashboard)/*` content.
- Old `(dashboard)/*` routes 301 → `/app/{current-ws-slug}/...`.
- `get_current_user` enforces `ws` claim presence on all `/app/*`
  API calls; old header reads still pass for legacy paths.

### Phase 3 — cleanup
- Remove `X-Workspace-Id` request interceptor.
- Remove `useWorkspaceStore` (zustand persist) — pure server-side
  state now.
- Remove `(dashboard)/*` route aliases.
- BE: drop header fallback in `get_current_user`.

### Phase 4 — Hub feature build-out
- /hub/members  — uses existing `/api/organizations/{id}/members`.
- /hub/billing  — relocate `/settings/billing` here, change scope
                  resolution to read org from user_token claim.
- /hub/security — SSO/SCIM/IP allowlist forms (BE already exists).
- /hub/audit    — uses existing audit router.
- /hub/settings — org name, billing email, branding.

### Phase 5 — Org switcher
- Multi-org users get an Org switcher in the Hub sidebar.
- Token model unchanged; switching org = exit-workspace +
  re-enter from the new org's Hub.

## Backward compatibility

During Phases 0–2 the old behaviour continues to work:
- `X-Workspace-Id` header reads still resolve the workspace.
- localStorage state still drives the switcher.
- Old `(dashboard)/*` routes still render.

Phase 3 is the **breaking commit** — at that point, every client
must be issuing workspace_tokens (no header fallback). Users with
stale tabs get a 401 on next request → forced re-login → bounce to
`/hub` → re-enter workspace → continue.

A future "client-version handshake" header would smooth this, but
v1 just accepts a one-time forced re-login. Document in the release
notes.

## Decision log

- **Why same cookie name across token types**: minimises FE state.
  The FE inspects `/api/auth/me` for `token_type` instead of
  juggling two cookie slots.
- **Why Linear-style switcher (not Slack-style /hub bounce)**:
  switching workspaces is a frequent action; round-tripping through
  /hub for every switch is annoying. The "Manage in Hub" affordance
  is still one click away.
- **Why URL slug + token claim both**: slug = shareable bookmark +
  readable URL. Token claim = the actual security boundary. URL
  slug must match the token's ws; on mismatch we 403 + offer to
  switch.
- **Why not workspace_id as path param + no claim**: every request
  would need a fresh DB membership check. Token claim caches the
  check at mint time + JWT signature verifies it cheaply.
- **Why a fresh ENTER endpoint instead of overloading login**:
  login is unauthenticated; ENTER requires an existing user_token.
  Mixing the two means login's failure mode (wrong password) and
  ENTER's failure mode (wrong workspace) share a status code.
- **Why no `wsv` (workspace version) claim for cache busting**:
  the token TTL is short (15 min). A workspace renamed or deleted
  shows up at the next refresh; the window is small enough to skip
  invalidation infrastructure.

## Risks + mitigations

| Risk | Mitigation |
|------|-----------|
| User mid-action when token expires + workspace was deleted in another tab | Refresh endpoint refuses to re-mint workspace_token for a vanished workspace; FE catches 401 → routes to /hub. |
| Cross-tab desync (tab A in ws-1, tab B in ws-2) | Two tabs share one cookie. Switching in tab A invalidates tab B's effective state. Document; advise users to use private windows for multi-workspace. Phase 5 could add per-tab token scoping. |
| Forgetting to gate a new route under `/app/*` | Route convention: every workspace-scoped page imports a shared `requireWorkspaceToken` server helper at the top. ESLint rule enforces. |
| Org-admin needs occasional workspace-level access (e.g. seed an agent for a team) | enter-workspace works for org-admins even without a `workspace_members` row — role promotion already handles this in `effective_workspace_role`. |
