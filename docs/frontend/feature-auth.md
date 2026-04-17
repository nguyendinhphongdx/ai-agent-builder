---
id: frontend-feature-auth
title: Auth Feature Module
domain: frontend
tags: [auth, login, register, jwt, hooks, forms, zod]
related: [frontend-api-client, api-auth-endpoints, frontend-layout]
summary: Documents the auth feature including types, service, hooks (useAuth, useLogin, useRegister, useLogout), views, and Zod-validated forms.
---

# Auth Feature

## Directory: `src/features/auth/`

### Barrel Export (`index.ts`)

Exports: `LoginView`, `RegisterView`, `useAuth`, `User` type.

## Types (`types/index.ts`)

| Type            | Fields                                                             |
|-----------------|--------------------------------------------------------------------|
| `User`          | `id`, `email`, `full_name`, `avatar_url`, `is_active`, `created_at` |
| `AuthResponse`  | `user: User`, `message: string`                                   |
| `LoginInput`    | `email`, `password`                                                |
| `RegisterInput` | `email`, `password`, `full_name?`                                  |

## Service (`services/authService.ts`)

Thin wrapper over `apiClient`:

| Method     | HTTP Call                    | Returns        |
|------------|------------------------------|----------------|
| `login`    | `POST /auth/login`           | `AuthResponse` |
| `register` | `POST /auth/register`        | `AuthResponse` |
| `logout`   | `POST /auth/logout`          | void           |
| `getMe`    | `GET /auth/me`               | `User`         |

## Hooks (`hooks/useAuth.ts`)

### Query Keys

```ts
authKeys.me = ["auth", "me"]
```

### useAuth()

- Uses `useQuery` with `authService.getMe`
- `retry: false` -- does not retry failed auth checks
- `staleTime: 5 minutes` -- caches user data for 5 min
- Returns: `{ user, isLoading, isAuthenticated: !!user, error }`

### useLogin()

- `useMutation` calling `authService.login`
- On success: sets query data for `authKeys.me` with `res.user`, navigates to `/`

### useRegister()

- `useMutation` calling `authService.register`
- On success: sets query data for `authKeys.me` with `res.user`, navigates to `/`

### useLogout()

- `useMutation` calling `authService.logout`
- On success: calls `queryClient.clear()` (wipes all cached data), navigates to `/login`

## Forms

### LoginForm (`components/LoginForm.tsx`)

- Zod schema: `email` (valid email), `password` (min 6 chars)
- Uses `react-hook-form` with `zodResolver`
- Fields: Email input, Password input
- Error display: "Invalid email or password" on mutation error
- Submit button shows "Signing in..." when pending
- Link to `/register` at bottom

### RegisterForm (`components/RegisterForm.tsx`)

- Zod schema: `email` (valid email), `password` (min 6 chars), `full_name` (optional)
- Fields: Full Name, Email, Password
- Error display: "Registration failed. Email may already be in use."
- Submit button shows "Creating account..." when pending
- Link to `/login` at bottom

## Views

### LoginView (`views/LoginView.tsx`)

Centered card with Bot icon, "Sign in" title, and `LoginForm`.

### RegisterView (`views/RegisterView.tsx`)

Centered card with Bot icon, "Create account" title, and `RegisterForm`.

Both views use full-screen centering with `min-h-screen` and `bg-background`.
