---
id: frontend-layout
title: Dashboard Layout, Sidebar, and Header
domain: frontend
tags: [layout, sidebar, header, navigation, auth-guard, dark-theme]
related: [frontend-app-router, frontend-feature-auth, frontend-providers]
summary: Documents the dashboard layout with auth guard, Sidebar navigation items, Header with user dropdown, and dark theme setup.
---

# Dashboard Layout

## File: `src/app/(dashboard)/layout.tsx`

This is a `"use client"` component that wraps all dashboard routes.

### Auth Guard

1. Calls `useAuth()` to get `isAuthenticated` and `isLoading`
2. If loading, shows a centered spinner on a `#08090a` background
3. If not authenticated after loading completes, redirects to `/login` via `router.push`
4. If not authenticated, returns `null` (renders nothing)

### Structure

```
<div class="flex h-screen bg-[#08090a] text-white">
  <Sidebar />
  <div class="flex flex-1 flex-col overflow-hidden">
    <Header />
    <main class="flex-1 overflow-auto">{children}</main>
  </div>
</div>
```

## Sidebar

**File:** `src/components/layout/Sidebar.tsx`

### Navigation Items

| Path         | Label      | Icon       |
|--------------|------------|------------|
| `/libraries` | Libraries  | `Library`  |
| `/tools`     | Tools      | `Wrench`   |
| `/workflows` | Workflows  | `GitBranch`|

Settings link is rendered separately at the bottom:

| Path        | Label    | Icon       |
|-------------|----------|------------|
| `/settings` | Settings | `Settings` |

### Active State Detection

A nav item is active when:
- `pathname === item.href`, OR
- `pathname.startsWith(item.href)` (for nested routes, excluding root `/`)

Active items get `bg-white/8 text-white font-medium`. Inactive items are `text-white/50` with hover effects.

### Branding

Top of sidebar shows the AgentForge logo: a cyan Bot icon in a `bg-white/8` rounded container with "AgentForge" text.

## Header

**File:** `src/components/layout/Header.tsx`

A minimal top bar (48px height) with content aligned to the right.

### User Menu

- Uses `useAuth()` to get the current user
- Shows an Avatar with initials derived from `full_name` (first letter of each word) or first letter of email
- Dropdown menu contains:
  - User email (read-only, muted text)
  - Logout button with `LogOut` icon
- Logout calls `apiClient.post("/auth/logout")` then navigates to `/login`

## Dark Theme Setup

The entire dashboard uses a dark theme:
- Background: `#08090a` (near-black)
- Sidebar background: `#0c0d0f`
- Borders: `border-white/6` (very subtle white borders)
- Text: white with varying opacity (`text-white`, `text-white/50`, `text-white/30`)
- The ThemeProvider defaults to `"dark"` theme via next-themes

## Design Tokens

| Element       | Color/Value     |
|---------------|-----------------|
| Page bg       | `#08090a`       |
| Sidebar bg    | `#0c0d0f`       |
| Header bg     | `#0c0d0f`       |
| Border        | `white/6`       |
| Active nav    | `white/8` bg    |
| Accent        | `cyan-400`      |
| Sidebar width | `w-56` (224px)  |
| Header height | `h-12` (48px)   |
