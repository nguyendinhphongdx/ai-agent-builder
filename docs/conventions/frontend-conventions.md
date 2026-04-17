---
id: conventions-frontend
title: Frontend Conventions - Feature Architecture & State Management
domain: conventions
tags: [conventions, frontend, nextjs, feature-based, thin-app-router, tanstack-query, zustand, import-rules]
related: [arch-project-structure, conventions-component-patterns, frontend-app-router]
summary: "Feature-based architecture. Thin App Router (pages only have metadata + View import). TanStack Query for server state, Zustand only for UI state. No cross-feature imports."
---

# Frontend Conventions

## Feature Module Structure (MUST follow)

```
features/{name}/
├── views/           # Page-level components (1 view = 1 route page)
├── components/      # UI components specific to this feature
├── hooks/           # TanStack Query hooks + custom logic
├── services/        # Pure Axios API call functions
├── stores/          # Zustand stores (ONLY if UI state needed)
├── types/           # TypeScript interfaces
└── index.ts         # Barrel export (public API)
```

## Thin App Router (MUST follow)

Page files contain ONLY metadata + View import:

```tsx
// app/(dashboard)/agents/page.tsx
import { Metadata } from "next";
import { AgentListView } from "@/features/agents/views/AgentListView";

export const metadata: Metadata = { title: "Agents | AgentForge" };
export default function AgentsPage() { return <AgentListView />; }
```

**NEVER put business logic, hooks, or state in page files.**

## Import Rules (MUST follow)

```
app/ → features/ (only via index.ts barrel)
features/ → components/ (shared UI)
features/ → lib/ (utilities)
features/ → hooks/ (shared hooks)
features/ ✗ features/ (NO cross-feature imports)
```

Exception: A feature can import types from another feature if needed.

## State Management

| What | Tool | Example |
|---|---|---|
| Server data (API responses) | TanStack Query | `useQuery`, `useMutation` |
| UI-only state | Zustand | streaming content, selected workflow node |
| Form state | React Hook Form | `useForm` with Zod resolver |
| URL state | Next.js router | `usePathname`, `useSearchParams` |

**NEVER use Zustand for data that comes from the API.** Use TanStack Query.

## Query Key Convention

```tsx
export const agentKeys = {
  all: ["agents"] as const,
  list: () => [...agentKeys.all, "list"] as const,
  detail: (id: string) => [...agentKeys.all, "detail", id] as const,
};
```

## Service Layer

```tsx
// Pure functions, no hooks, no state
export const agentService = {
  list: () => apiClient.get<Agent[]>("/agents").then((r) => r.data),
  getById: (id: string) => apiClient.get<Agent>(`/agents/${id}`).then((r) => r.data),
};
```

## Themes
- **Landing page** (`/`): light theme, white background
- **Dashboard** (`/(dashboard)/`): dark theme, `bg-[#08090a]`
- **Auth pages**: light theme
