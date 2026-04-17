---
id: conventions-api
title: API Conventions - REST, Status Codes, Auth, Errors
domain: conventions
tags: [conventions, api, rest, status-codes, auth, cookies, cors, pagination, errors]
related: [conventions-backend, api-auth-endpoints]
summary: "REST API at /api prefix. JWT in httpOnly cookies. Standard status codes. Error format: {detail: string}. Pagination via limit/offset query params."
---

# API Conventions

## Base URL
All endpoints under `/api` prefix. Example: `GET /api/agents`

## Authentication
- JWT tokens in **httpOnly secure cookies** (NOT Authorization header)
- Cookie names: `access_token` (path=/), `refresh_token` (path=/api/auth/refresh)
- Cookie flags: `httponly=True, secure=True, samesite=lax`
- Protected endpoints use `Depends(get_current_user)` dependency

## CORS
```python
allow_origins=["http://localhost:3000"]
allow_credentials=True  # Required for cookies
allow_methods=["*"]
allow_headers=["*"]
```

## Status Codes

| Code | When |
|---|---|
| 200 | Success (GET, PUT) |
| 201 | Created (POST) |
| 204 | Deleted (DELETE, no body) |
| 400 | Bad request (validation error) |
| 401 | Not authenticated |
| 403 | Forbidden (account disabled) |
| 404 | Not found |
| 409 | Conflict (email already exists) |

## Error Format

```json
{"detail": "Agent not found"}
```

FastAPI validation errors:
```json
{"detail": [{"loc": ["body", "name"], "msg": "field required", "type": "value_error.missing"}]}
```

## Pagination

```
GET /api/conversations/{id}/messages?limit=100&offset=0
```
- `limit`: max items (default 100, max 200)
- `offset`: skip items (default 0)

## Request/Response

- Content-Type: `application/json` (except file upload: `multipart/form-data`)
- All IDs are UUID strings
- Timestamps in ISO 8601 format
- JSONB fields returned as-is (dict/list)

## WebSocket

```
WS /api/ws/chat/{conversation_id}?token={access_token}
```
Auth via query param OR cookie. Protocol documented in `api/websocket-protocol.md`.
