---
id: flows-user-registration
title: User Registration Flow
domain: flows
tags: [auth, registration, cookies, redirect, onboarding]
related: [api-auth-endpoints, frontend-feature-auth, frontend-layout]
summary: End-to-end flow from register form submission through cookie setting, query cache update, redirect, and dashboard loading.
---

# User Registration Flow

## Overview

New user submits the registration form and is redirected to the authenticated dashboard.

## Step-by-Step

### 1. User Fills Register Form

**Component:** `RegisterForm` at `/register`

- User enters Full Name (optional), Email, Password
- Zod validates: email format, password min 6 chars
- Submit triggers `useRegister().mutate(data)`

### 2. Frontend Sends Register Request

**Service:** `authService.register(data)`

```
POST /api/auth/register
Body: { email, password, full_name }
```

### 3. Backend Creates User

**Handler:** `app/modules/identity/auth/router.py` -> `register()`

1. Checks if email already exists -> 409 if duplicate
2. Calls `create_user(db, email, password, full_name)` which hashes the password
3. Calls `_set_auth_cookies(response, user_id)`:
   - Creates JWT access token (short-lived)
   - Creates JWT refresh token (long-lived)
   - Sets `access_token` cookie (httpOnly, secure, path `/`)
   - Sets `refresh_token` cookie (httpOnly, secure, path `/api/auth/refresh`)
4. Returns `AuthResponse` with user data

### 4. Frontend Handles Success

**Hook:** `useRegister()` -> `onSuccess`

1. Sets query data for `["auth", "me"]` key with `res.user` (instant cache population)
2. Calls `router.push("/")` to navigate to dashboard root

### 5. Dashboard Layout Auth Check

**Component:** `(dashboard)/layout.tsx`

1. `useAuth()` finds cached user data from step 4 -> `isAuthenticated: true`
2. No redirect to login, renders Sidebar + Header + main content

### 6. Dashboard Root Redirect

**Component:** `(dashboard)/page.tsx`

Server-side `redirect("/libraries")` sends user to the Libraries view.

### 7. Libraries Page Loads

**Component:** `AgentLibraryView`

1. `useAgents()` fetches agent list (empty for new user)
2. Shows empty state: "No agents yet" with "Create your first agent" button

## Error Handling

| Error         | Frontend Behavior                                    |
|---------------|------------------------------------------------------|
| 409 Conflict  | Shows "Registration failed. Email may already be in use." |
| Network error | React Query mutation error, same message displayed    |
| Zod validation| Inline field errors before submission                 |

## Cookie Lifecycle

After registration, the browser holds:
- `access_token`: sent with all `/api/*` requests via `withCredentials: true`
- `refresh_token`: sent only to `/api/auth/refresh` (restricted path)
- Both httpOnly (not accessible to JavaScript)
