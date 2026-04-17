---
id: frontend-api-client
title: Axios API Client and Endpoint Constants
domain: frontend
tags: [api, axios, http, interceptor, refresh-token, endpoints]
related: [frontend-feature-auth, api-auth-endpoints]
summary: Documents the Axios client configuration with withCredentials, the 401 refresh interceptor, and the API endpoint constants map.
---

# API Client

## File: `src/lib/api/client.ts`

### Axios Instance Configuration

```ts
const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});
```

- **baseURL:** Reads from `NEXT_PUBLIC_API_URL` env var, defaults to `http://localhost:8000/api`
- **withCredentials:** `true` -- automatically sends httpOnly cookies (access_token, refresh_token) with every request
- **Content-Type:** JSON by default

### Refresh Token Interceptor

The response interceptor handles automatic token refresh on 401 errors:

1. On 401 response, checks `original._retry` to prevent infinite loops
2. Sets `_retry = true` on the original request config
3. POSTs to `/auth/refresh` (with credentials) to get new tokens
4. On success, retries the original request with `apiClient(original)`
5. On refresh failure, redirects to `/login` via `window.location.href`

Key behaviors:
- Only retries once per request (the `_retry` flag)
- Uses raw `axios.post` (not `apiClient`) for the refresh call to avoid interceptor recursion
- Client-side only redirect check (`typeof window !== "undefined"`)

## Endpoint Constants

**File:** `src/lib/api/endpoints.ts`

The `API` constant organizes all endpoint paths:

### auth
| Key      | Path              |
|----------|-------------------|
| register | `/auth/register`  |
| login    | `/auth/login`     |
| logout   | `/auth/logout`    |
| refresh  | `/auth/refresh`   |
| me       | `/auth/me`        |

### agents
| Key        | Path                                    |
|------------|-----------------------------------------|
| list       | `/agents`                               |
| create     | `/agents`                               |
| detail     | `/agents/${id}`                         |
| attachTool | `/agents/${agentId}/tools/${toolId}`     |
| attachKB   | `/agents/${agentId}/knowledge-bases/${kbId}` |

### tools
| Key    | Path               |
|--------|--------------------|
| list   | `/tools`           |
| create | `/tools`           |
| detail | `/tools/${id}`     |
| test   | `/tools/${id}/test`|

### knowledgeBases
| Key       | Path                               |
|-----------|------------------------------------|
| list      | `/knowledge-bases`                 |
| create    | `/knowledge-bases`                 |
| detail    | `/knowledge-bases/${id}`           |
| documents | `/knowledge-bases/${id}/documents` |
| query     | `/knowledge-bases/${id}/query`     |

### workflows
| Key     | Path                          |
|---------|-------------------------------|
| list    | `/workflows`                  |
| create  | `/workflows`                  |
| detail  | `/workflows/${id}`            |
| execute | `/workflows/${id}/execute`    |

### conversations
| Key      | Path                                |
|----------|-------------------------------------|
| list     | `/conversations`                    |
| create   | `/conversations`                    |
| detail   | `/conversations/${id}`              |
| messages | `/conversations/${id}/messages`     |

The object is typed `as const` for full type safety on endpoint paths.
