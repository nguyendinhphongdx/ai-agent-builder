---
id: architecture-socket-service
title: Socket Service (NestJS)
domain: architecture
tags: [socket, websocket, realtime, nestjs, socket.io, events, rooms]
related: [api-websocket-protocol, frontend-websocket-client]
summary: Documents the NestJS Socket Service — architecture, rooms, emit API, frontend integration, and event conventions for real-time features.
---

# Socket Service

Standalone NestJS service that manages real-time WebSocket connections via Socket.IO. Backend services (Python FastAPI) push events to clients through this service via HTTP.

## Architecture

```
┌──────────────┐     HTTP POST      ┌──────────────────┐    Socket.IO    ┌──────────────┐
│ Python       │ ──────────────────> │ NestJS Socket    │ ─────────────> │ Frontend     │
│ Backend      │  /emit, /emit/room │ Service (:4000)  │   ws://        │ (browser)    │
│ (FastAPI)    │  x-api-secret      │                  │                │              │
└──────────────┘                    └──────────────────┘                └──────────────┘
```

**Why separate service?**
- Python backend is async but not real-time — no native WebSocket server
- NestJS + Socket.IO handles connection management, rooms, reconnection
- Backend pushes events via simple HTTP calls — no WebSocket state management needed

## Service Details

| Setting | Value |
|---------|-------|
| **Port** | `4000` (configurable via `PORT` env) |
| **Transport** | Socket.IO over WebSocket |
| **Auth** | JWT token in `socket.handshake.auth.token` |
| **CORS** | All origins (configurable via `CORS_ORIGIN`) |
| **Location** | `services/socket/` |

## Rooms

Rooms are namespaces that group connected clients. A client can be in multiple rooms.

### Auto-joined rooms

| Room | Format | When |
|------|--------|------|
| **User room** | `user:{userId}` | On connect — every user auto-joins their personal room |
| **Token rooms** | From JWT `rooms` claim | On connect — if token has `rooms: ["room1", "room2"]` |

### Application rooms

Rooms that clients join based on what they're viewing:

| Room | Format | Use case |
|------|--------|----------|
| **Workflow editor** | `workflow:{workflowId}` | Real-time node execution status during workflow run |
| **Conversation** | `conversation:{conversationId}` | Chat streaming (currently handled via separate WS) |
| **Agent** | `agent:{agentId}` | Agent execution events |

**Frontend joins a room** by emitting or by having it in the JWT token. For workflow rooms, the frontend should join when entering the workflow editor and leave when navigating away.

## Emit API (Backend → Client)

Backend services push events to clients via HTTP POST to the socket service.

### Authentication

All emit endpoints require `x-api-secret` header matching `API_SECRET` env var.

```
Headers:
  x-api-secret: <shared secret>
  Content-Type: application/json
```

### Endpoints

#### POST /emit — Send to specific user

```json
{
  "userId": "uuid-string",
  "event": "agent:complete",
  "payload": { "agentId": "...", "name": "..." }
}
```

Emits to room `user:{userId}`.

#### POST /emit/room — Send to room

```json
{
  "room": "workflow:abc-123",
  "event": "node:completed",
  "payload": { "nodeId": "...", "items": [...] }
}
```

Emits to all clients in the specified room.

#### POST /emit/broadcast — Send to everyone

```json
{
  "event": "system:maintenance",
  "payload": { "message": "Maintenance in 5 minutes" }
}
```

Emits to all connected clients.

### Envelope Format

All events are wrapped in a standard envelope:

```typescript
interface SocketEnvelope {
  event: string;        // Event name (same as the one sent)
  payload: object;      // Event data
  timestamp: string;    // ISO 8601 when the socket service processed it
}
```

## Event Conventions

### Naming

Events use `domain:action` format:

```
node:running        — Workflow node started execution
node:completed      — Workflow node finished successfully
node:failed         — Workflow node failed with error
workflow:completed  — Entire workflow finished
workflow:failed     — Entire workflow failed
agent:complete      — Agent execution completed
```

### Workflow Execution Events

Events emitted to room `workflow:{workflowId}` during execution:

| Event | Payload | When |
|-------|---------|------|
| `node:running` | `{ nodeId, nodeType, label }` | Node starts executing |
| `node:completed` | `{ nodeId, nodeType, label, outputItemsCount, tokensUsed }` | Node finished successfully |
| `node:failed` | `{ nodeId, nodeType, label, error }` | Node execution failed |
| `workflow:completed` | `{ runId, totalTokens, outputItemsCount }` | Workflow finished |
| `workflow:failed` | `{ runId, error }` | Workflow failed |

## Frontend Integration

### SocketProvider

Wraps the app, connects on auth, provides context:

```tsx
// components/providers/SocketProvider.tsx
// Auto-connects when authenticated, disconnects on logout
// Provides { socket, isConnected } via SocketContext
```

### useSocket()

Access the socket instance:

```tsx
const { socket, isConnected } = useSocket();
```

### useSocketEvent(event, handler)

Subscribe to events:

```tsx
useSocketEvent("node:completed", (payload) => {
  console.log("Node done:", payload.nodeId);
});
```

### Joining rooms

Frontend should join workflow room when entering editor:

```tsx
// In WorkflowEditorView
useEffect(() => {
  if (!socket || !isConnected) return;
  socket.emit("join", { room: `workflow:${workflowId}` });
  return () => {
    socket.emit("leave", { room: `workflow:${workflowId}` });
  };
}, [socket, isConnected, workflowId]);
```

> **Note:** The socket gateway currently only supports auto-join via JWT `rooms` claim. To support dynamic `join`/`leave`, a handler needs to be added to `SocketGateway`. See "Missing Features" below.

## Python Backend Usage

Utility to emit events from Python:

```python
import httpx

SOCKET_SERVICE_URL = "http://localhost:4000"
API_SECRET = "change-me"  # Match socket service config

async def emit_to_room(room: str, event: str, payload: dict):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SOCKET_SERVICE_URL}/emit/room",
            json={"room": room, "event": event, "payload": payload},
            headers={"x-api-secret": API_SECRET},
        )

# Usage in WorkflowRunner:
await emit_to_room(
    room=f"workflow:{workflow_id}",
    event="node:running",
    payload={"nodeId": node_id, "nodeType": "llm", "label": "GPT-4o Call"},
)
```

## File Structure

```
services/socket/
├── src/
│   ├── main.ts                          # NestJS bootstrap (:4000)
│   ├── app.module.ts                    # Root module
│   ├── config/
│   │   └── index.ts                     # app, auth, redis configs
│   ├── auth/
│   │   ├── auth.module.ts
│   │   └── jwt.service.ts               # JWT verification (shared secret with Python)
│   ├── gateway/
│   │   ├── gateway.module.ts
│   │   └── socket.gateway.ts            # Socket.IO gateway (connect, disconnect, rooms)
│   ├── connections/
│   │   ├── connections.module.ts
│   │   └── connections.service.ts        # Track userId ↔ socketId mapping
│   ├── emit/
│   │   ├── emit.module.ts
│   │   ├── emit.controller.ts           # HTTP endpoints for pushing events
│   │   ├── emit.dto.ts                  # Request DTOs (EmitToUserDto, EmitToRoomDto, BroadcastDto)
│   │   └── emit.guard.ts               # x-api-secret validation
│   └── health/
│       ├── health.module.ts
│       └── health.controller.ts         # Health check endpoint
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `4000` | HTTP + WebSocket port |
| `CORS_ORIGIN` | `http://localhost:3000` | Allowed CORS origins |
| `SECRET_KEY` | `change-me` | JWT secret (must match Python backend) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `API_SECRET` | `change-me` | Shared secret for emit API auth |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for Socket.IO adapter (future) |

## Missing Features (TODO)

1. **Dynamic room join/leave** — Gateway needs `@SubscribeMessage('join')` / `@SubscribeMessage('leave')` handlers for client-side room management
2. **Redis adapter** — For horizontal scaling, Socket.IO needs `@socket.io/redis-adapter` to share state across instances
3. **Room authorization** — Verify that user has permission to join a room (e.g., workflow belongs to user)
4. **Connection rate limiting** — Prevent connection flood
5. **Heartbeat/ping** — Custom ping interval for connection health monitoring
