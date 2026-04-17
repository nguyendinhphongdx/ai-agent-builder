---
id: frontend-app-router
title: Next.js App Router Structure
domain: frontend
tags: [routing, next.js, app-router, pages, metadata]
related: [frontend-layout, frontend-providers, frontend-feature-auth]
summary: Documents all 14 routes across two route groups (auth and dashboard), metadata export rules, and when to use the "use client" directive.
---

# App Router Structure

## Route Groups

The app uses Next.js App Router with two route groups under `apps/frontend/src/app/`:

### (auth) Group -- Public Routes

| Route          | File                         | Component     | Metadata Title                |
|----------------|------------------------------|---------------|-------------------------------|
| `/login`       | `(auth)/login/page.tsx`      | `LoginView`   | "Sign In \| AI Agent Builder" |
| `/register`    | `(auth)/register/page.tsx`   | `RegisterView`| "Create Account \| AI Agent Builder" |

These pages are server components that export static `metadata` and render feature views.

### (dashboard) Group -- Protected Routes

All dashboard routes share `(dashboard)/layout.tsx`, which is a `"use client"` component providing the auth guard, Sidebar, and Header.

| Route                      | File                                  | Component            | Metadata Title             |
|----------------------------|---------------------------------------|----------------------|----------------------------|
| `/` (dashboard index)      | `(dashboard)/page.tsx`                | `redirect("/libraries")` | N/A (server redirect)  |
| `/libraries`               | `(dashboard)/libraries/page.tsx`      | `AgentLibraryView`   | "Libraries \| AgentForge"  |
| `/agents`                  | `(dashboard)/agents/page.tsx`         | `AgentListView`      | "Agents \| AI Agent Builder"|
| `/agents/new`              | `(dashboard)/agents/new/page.tsx`     | `AgentEditorView`    | "New Agent \| AgentForge"  |
| `/agents/[id]`             | `(dashboard)/agents/[id]/page.tsx`    | `AgentEditorView`    | N/A (client component)     |
| `/agents/[id]/chat`        | `(dashboard)/agents/[id]/chat/page.tsx` | `ChatView`         | N/A (client component)     |
| `/tools`                   | `(dashboard)/tools/page.tsx`          | `ToolListView`       | "Tools \| AgentForge"      |
| `/workflows`               | `(dashboard)/workflows/page.tsx`      | `WorkflowListView`   | "Workflows \| AgentForge"  |
| `/workflows/[id]`          | `(dashboard)/workflows/[id]/page.tsx` | `WorkflowEditorView` | N/A (client component)     |
| `/knowledge`               | `(dashboard)/knowledge/page.tsx`      | Placeholder          | "Knowledge Bases \| AI Agent Builder" |
| `/settings`                | `(dashboard)/settings/page.tsx`       | `SettingsView`       | "Settings \| AgentForge"   |

### Root-Level

| Route | File           | Component      | Notes                      |
|-------|----------------|----------------|----------------------------|
| `/`   | `page.tsx`     | `LandingPage`  | Public marketing/landing page |

## Root Layout

`app/layout.tsx` is a server component that sets up the HTML shell:

- Loads Inter font from Google Fonts
- Exports root `metadata` (title: "AI Agent Builder")
- Wraps all children in `<Providers>`
- Sets `suppressHydrationWarning` on `<html>` for next-themes compatibility

## Metadata Export Rules

- **Server component pages** export `metadata` as a named const (static metadata).
- **Client component pages** (those using `"use client"` or `use()` for params) cannot export metadata. The parent server page in `/agents/new/page.tsx` exports metadata instead.
- Dynamic route pages (`[id]`) use `"use client"` with React `use()` to unwrap the `params` Promise.

## When to Use "use client"

Pages that need `"use client"`:

1. **Dashboard layout** -- uses `useAuth()`, `useRouter()`, `useEffect()`
2. **Dynamic [id] pages** -- use `use(params)` to unwrap the async params Promise
3. **Landing page** is a server component (no directive needed)
4. **Static pages** (login, register, tools, workflows list) are server components that delegate to client feature views

Rule of thumb: page files stay as server components when they only import a view and export metadata. They become client components only when they need to read dynamic params via `use()`.
