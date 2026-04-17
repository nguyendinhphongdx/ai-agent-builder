---
id: backend-auth
title: Authentication
domain: backend
tags: [auth, jwt, cookie, bcrypt, security]
related: [backend-config, backend-database]
summary: JWT-based auth via httpOnly cookies, bcrypt password hashing, access/refresh token flow, and get_current_user dependency.
---

# Authentication

## Overview

Authentication uses stateless JWT tokens stored in httpOnly cookies. The system
issues two tokens on login/register: a short-lived access token and a long-lived
refresh token. Passwords are hashed with bcrypt. A FastAPI dependency extracts and
validates the access token from cookies on every protected request.

## Specification

### Password Hashing

- Library: `passlib` with `CryptContext(schemes=["bcrypt"])`.
- `hash_password(plain) -> str` produces a bcrypt hash.
- `verify_password(plain, hashed) -> bool` verifies a password against its hash.

### Token Structure

Both access and refresh tokens are JWTs signed with HS256.

**Access token payload:**
```json
{ "sub": "<user_id>", "type": "access", "exp": <utc_timestamp> }
```

**Refresh token payload:**
```json
{ "sub": "<user_id>", "type": "refresh", "exp": <utc_timestamp> }
```

- Signed with `settings.SECRET_KEY` using `settings.ALGORITHM` (HS256).
- Library: `python-jose` (`jose.jwt`).

### Token Lifetimes

| Token | Setting | Default |
|---|---|---|
| Access | `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 minutes |
| Refresh | `REFRESH_TOKEN_EXPIRE_DAYS` | 7 days |

### Cookie Configuration

| Property | access_token | refresh_token |
|---|---|---|
| `httponly` | `True` | `True` |
| `secure` | `True` | `True` |
| `samesite` | `lax` | `lax` |
| `path` | `/` | `/api/auth/refresh` |
| `max_age` | `ACCESS_TOKEN_EXPIRE_MINUTES * 60` | `REFRESH_TOKEN_EXPIRE_DAYS * 86400` |

The refresh token cookie is scoped to `/api/auth/refresh` so the browser only
sends it when hitting the refresh endpoint.

### Endpoints

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/api/auth/register` | Create account, set cookies, return user | No |
| `POST` | `/api/auth/login` | Verify credentials, set cookies, return user | No |
| `POST` | `/api/auth/refresh` | Issue new token pair from refresh cookie | Refresh cookie |
| `POST` | `/api/auth/logout` | Delete both cookies | No |
| `GET` | `/api/auth/me` | Return current user info | Access cookie |

### Refresh Flow

1. Client calls `POST /api/auth/refresh` (browser auto-sends refresh cookie).
2. Server decodes refresh token, verifies `type == "refresh"`.
3. Looks up user by `sub`, checks `is_active`.
4. Issues new access + refresh token pair in cookies.

### `get_current_user` Dependency

```python
async def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User
```

1. Reads `access_token` from cookies.
2. Decodes JWT, verifies `type == "access"`.
3. Extracts `sub` (user ID), queries the database.
4. Checks `user.is_active`.
5. Returns `User` or raises `HTTP 401`.

### Schemas

| Schema | Fields |
|---|---|
| `RegisterRequest` | `email` (EmailStr), `password` (str), `full_name` (str, optional) |
| `LoginRequest` | `email` (EmailStr), `password` (str) |
| `UserResponse` | `id`, `email`, `full_name`, `avatar_url`, `is_active`, `created_at` |
| `AuthResponse` | `user` (UserResponse), `message` (default `"ok"`) |

## File Structure

```
apps/backend/app/auth/
  __init__.py
  dependencies.py    # get_current_user
  router.py          # /auth endpoints
  schemas.py         # Pydantic request/response models
  service.py         # JWT creation/decode, password hashing, user queries
```

## Key Functions / Classes

| Function | File | Purpose |
|---|---|---|
| `hash_password` | `service.py` | bcrypt hash |
| `verify_password` | `service.py` | bcrypt verify |
| `create_access_token` | `service.py` | Short-lived JWT |
| `create_refresh_token` | `service.py` | Long-lived JWT |
| `decode_token` | `service.py` | Decode JWT, return payload or None |
| `get_user_by_email` | `service.py` | DB lookup by email |
| `get_user_by_id` | `service.py` | DB lookup by UUID |
| `create_user` | `service.py` | Insert new user with hashed password |
| `get_current_user` | `dependencies.py` | FastAPI dependency for protected routes |
| `_set_auth_cookies` | `router.py` | Sets both cookies on Response |

## Examples

```python
# Protecting a route
from app.auth.dependencies import get_current_user

@router.get("/my-resource")
async def my_endpoint(user: User = Depends(get_current_user)):
    return {"owner": str(user.id)}
```

### Constraints

- All protected endpoints MUST use `Depends(get_current_user)`.
- Passwords MUST be hashed with bcrypt before storage; never store plaintext.
- `SECRET_KEY` MUST be changed from the default in any deployed environment.
- The refresh token cookie path MUST be `/api/auth/refresh` to limit exposure.
- Login MUST reject inactive users with HTTP 403.
