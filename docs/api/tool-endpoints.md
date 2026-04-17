---
id: api-tool-endpoints
title: Tool API Endpoints
domain: api
tags: [tools, crud, testing, registry, execution]
related: [frontend-feature-tools, api-agent-endpoints, flows-tool-execution]
summary: Documents Tool CRUD endpoints and the test endpoint that builds and invokes tools via the tool registry.
---

# Tool API Endpoints

**Router:** `app/tools/router.py`  
**Prefix:** `/api/tools`  
**Auth:** All endpoints require `get_current_user`.

## GET /tools

List all tools owned by the current user.

**Response (200):**
```json
[
  {
    "id": "uuid", "name": "Search API", "description": "Search product catalog",
    "tool_type": "http_request", "config": {"method": "GET", "url": "https://api.example.com/search?q={query}"},
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
    "output_schema": null, "is_active": true, "timeout_seconds": 30,
    "created_at": "...", "updated_at": "..."
  }
]
```

## POST /tools

Create a new tool.

**Request:**
```json
{
  "name": "Search API",
  "description": "Search the product catalog by name",
  "tool_type": "http_request",
  "config": {"method": "GET", "url": "https://api.example.com/search?q={query}", "headers": {}},
  "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "Search term"}}, "required": ["query"]},
  "timeout_seconds": 30
}
```

**Response (201):** Full `ToolResponse`.

## GET /tools/{tool_id}

Get tool detail.

**Response (200):** `ToolResponse`.

**Errors:** 404 if tool not found or not owned by user.

## PUT /tools/{tool_id}

Update tool fields (partial update via `exclude_unset`).

**Request:** Any subset of `ToolUpdate` fields.

**Response (200):** Updated `ToolResponse`.

## DELETE /tools/{tool_id}

Delete a tool.

**Response:** 204 No Content.

## POST /tools/{tool_id}/test

Test a tool with sample input data. Uses the `tool_registry` to build and invoke the tool.

**Request:**
```json
{ "input_data": {"query": "laptop"} }
```

**Response (200):**
```json
{ "success": true, "result": "Found 42 products...", "error": null, "latency_ms": 234 }
```

On failure:
```json
{ "success": false, "result": null, "error": "Connection timeout", "latency_ms": 5003 }
```

### Test Implementation

1. Loads the tool record from DB
2. Calls `tool_registry.build(tool)` to create a LangChain `StructuredTool`
3. Invokes the tool with `await lc_tool.ainvoke(body.input_data)`
4. Measures latency and returns success/failure with result or error message
5. Exceptions are caught and returned as `success: false` with error string

## Tool Types

The backend supports these `tool_type` values: `http_request`, `code_exec`, `db_query`, `web_scrape`, `custom_function`. Each has a corresponding builder in the tool registry.
