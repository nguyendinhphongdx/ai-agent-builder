---
id: frontend-websocket-client
title: WebSocket Client for Chat Streaming
domain: frontend
tags: [websocket, streaming, chat, real-time]
related: [frontend-feature-chat, api-websocket-protocol]
summary: Documents the createChatWS() factory function, WSMessage discriminated union types, and the handler callback interface.
---

# WebSocket Client

## File: `src/lib/ws/client.ts`

### WSMessage Types

The client defines a discriminated union for all server-to-client messages:

```ts
type WSMessage =
  | { type: "token"; content: string }       // Streaming text chunk
  | { type: "tool_start"; name: string }     // Tool execution began
  | { type: "tool_end"; name: string; result: string }  // Tool execution completed
  | { type: "done" }                         // Response fully complete
  | { type: "error"; message: string }       // Error occurred
```

### createChatWS(options)

Factory function that creates a WebSocket connection and wires up message dispatching.

**Parameters (ChatWSOptions):**

| Field            | Type                                      | Description                         |
|------------------|-------------------------------------------|-------------------------------------|
| `conversationId` | `string`                                  | ID of the conversation to connect   |
| `onToken`        | `(content: string) => void`               | Called for each streaming text chunk |
| `onToolStart`    | `(name: string) => void`                  | Called when a tool starts executing  |
| `onToolEnd`      | `(name: string, result: string) => void`  | Called when a tool finishes          |
| `onDone`         | `() => void`                              | Called when response is complete     |
| `onError`        | `(message: string) => void`               | Called on error or WS failure        |

### Connection URL

```
${NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api"}/ws/chat/${conversationId}
```

Reads from `NEXT_PUBLIC_WS_URL` env var, defaults to `ws://localhost:8000/api`.

### Message Dispatching

The `ws.onmessage` handler parses incoming JSON and dispatches by `type` field using a switch statement. The `ws.onerror` handler calls `onError` with a generic connection error message.

### Return Value

Returns an object with:

| Method/Property | Description                                    |
|-----------------|------------------------------------------------|
| `send(content)` | Sends `{ content }` JSON if WS is OPEN        |
| `close()`       | Closes the WebSocket connection                |
| `readyState`    | Getter returning current `ws.readyState`       |

### Client-to-Server Messages

The client sends a single message format:

```json
{ "content": "user message text" }
```

Only sent when `ws.readyState === WebSocket.OPEN`.

### Usage Pattern

```ts
const ws = createChatWS({
  conversationId: "uuid",
  onToken: (chunk) => appendToStream(chunk),
  onToolStart: (name) => showToolIndicator(name),
  onToolEnd: () => hideToolIndicator(),
  onDone: () => finalizeMessage(),
  onError: (msg) => showError(msg),
});

ws.send("Hello, agent!");
// later...
ws.close();
```
