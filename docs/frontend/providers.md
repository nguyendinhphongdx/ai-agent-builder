---
id: frontend-providers
title: Provider Composition
domain: frontend
tags: [providers, react-query, theme, next-themes, tanstack]
related: [frontend-app-router, frontend-layout]
summary: Documents the Providers.tsx composition tree including QueryProvider, ThemeProvider, and Toaster setup.
---

# Provider Composition

## File: `src/components/providers/Providers.tsx`

The root `Providers` component wraps the entire application. It is a `"use client"` component and is mounted in the root `layout.tsx`.

```
<QueryProvider>
  <ThemeProvider>
    {children}
    <Toaster />
  </ThemeProvider>
</QueryProvider>
```

## QueryProvider

**File:** `src/components/providers/QueryProvider.tsx`

Wraps children with TanStack React Query's `QueryClientProvider`.

Configuration:
- **staleTime:** 60 seconds (1 minute) -- queries are considered fresh for 60s before refetching
- **retry:** 1 -- failed queries retry once before surfacing error
- QueryClient is created with `useState` to ensure one instance per component lifecycle (prevents re-creation on re-renders)

## ThemeProvider

**File:** `src/components/providers/ThemeProvider.tsx`

Wraps children with `next-themes` ThemeProvider.

Configuration:
- **attribute:** `"class"` -- applies theme via CSS class on `<html>`
- **defaultTheme:** `"dark"` -- dark mode by default
- **enableSystem:** `true` -- respects OS preference
- **disableTransitionOnChange:** `true` -- prevents flash of transition when switching themes

## Toaster

Uses `sonner` toast library via `@/components/ui/sonner`. Rendered as a sibling to `{children}` inside ThemeProvider so toasts pick up the active theme.

## Composition Order

The nesting order matters:
1. **QueryProvider** outermost -- all components can use `useQuery`/`useMutation`
2. **ThemeProvider** inside -- theme context available to all UI
3. **Toaster** at the end -- floats above page content

## Usage

Mounted once in `app/layout.tsx`:

```tsx
<Providers>{children}</Providers>
```

All pages, layouts, and features automatically inherit query caching and theme support without additional setup.
