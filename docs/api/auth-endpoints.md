---
id: api-auth-endpoints
title: Auth API Endpoints
domain: api
tags: [auth, jwt, cookies, register, login, refresh, logout]
related: [frontend-feature-auth, frontend-api-client]
summary: Documents POST register/login/refresh/logout and GET me endpoints with httpOnly cookie-based JWT authentication.
---

# Auth API Endpoints

**Router:** `app/auth/router.py`  
**Prefix:** `/api/auth`

## Authentication Model

Uses httpOnly cookies for both access and refresh tokens:
- `access_token`: path `/`, expires after `ACCESS_TOKEN_EXPIRE_MINUTES`
- `refresh_token`: path `/api/auth/refresh` only, expires after `REFRESH_TOKEN_EXPIRE_DAYS`
- Both cookies: `httponly=True`, `secure=True`, `samesite="lax"`

## POST /auth/register

Creates a new user account.

**Request:**
```json
{ "email": "user@example.com", "password": "secret123", "full_name": "John Doe" }
```

**Response (201):**
```json
{
  "user": {
    "id": "uuid", "email": "user@example.com", "full_name": "John Doe",
    "avatar_url": null, "is_active": true, "created_at": "2026-01-01T00:00:00Z"
  },
  "message": "ok"
}
```

**Errors:** 409 if email already registered.

**Side Effects:** Sets `access_token` and `refresh_token` cookies.

## POST /auth/login

Authenticates user with email and password.

**Request:**
```json
{ "email": "user@example.com", "password": "secret123" }
```

**Response (200):** Same `AuthResponse` format as register.

**Errors:**
- 401: Invalid email or password
- 403: Account is disabled

**Side Effects:** Sets auth cookies, updates `last_login_at` on user record.

## POST /auth/refresh

Refreshes the access token using the refresh token cookie.

**Request:** No body. Reads `refresh_token` from cookie.

**Response (200):** Same `AuthResponse` format.

**Errors:**
- 401: No refresh token, invalid/expired token, invalid payload, user not found/inactive

**Side Effects:** Sets new `access_token` and `refresh_token` cookies.

## POST /auth/logout

Clears authentication cookies.

**Request:** No body.

**Response (200):**
```json
{ "message": "Logged out" }
```

**Side Effects:** Deletes `access_token` (path `/`) and `refresh_token` (path `/api/auth/refresh`) cookies.

## GET /auth/me

Returns the currently authenticated user.

**Auth:** Requires valid `access_token` cookie (via `get_current_user` dependency).

**Response (200):**
```json
{
  "id": "uuid", "email": "user@example.com", "full_name": "John Doe",
  "avatar_url": null, "is_active": true, "created_at": "2026-01-01T00:00:00Z"
}
```

**Errors:** 401 if not authenticated.

## Schemas

| Schema           | Fields                                                      |
|------------------|-------------------------------------------------------------|
| `RegisterRequest`| `email: EmailStr`, `password: str`, `full_name: str?`      |
| `LoginRequest`   | `email: EmailStr`, `password: str`                          |
| `UserResponse`   | `id`, `email`, `full_name`, `avatar_url`, `is_active`, `created_at` |
| `AuthResponse`   | `user: UserResponse`, `message: str = "ok"`                 |
