---
id: api-workflow-endpoints
title: Workflow API Endpoints
domain: api
tags: [workflows, crud, execution, graph, runs, langgraph]
related: [frontend-feature-workflows, flows-workflow-execution]
summary: Documents Workflow CRUD, graph save, execute, and run history endpoints with request/response examples.
---

# Workflow API Endpoints

**Router:** `app/workflows/router.py`  
**Prefix:** `/api/workflows`  
**Auth:** All endpoints require `get_current_user`.

## GET /workflows

List all workflows owned by the current user.

**Response (200):** `WorkflowListResponse[]` with `id`, `name`, `description`, `version`, `is_active`, `created_at`, `updated_at`.

## POST /workflows

Create a new empty workflow.

**Request:**
```json
{ "name": "Customer Support Flow", "description": "Handles support tickets" }
```

**Response (201):** `WorkflowResponse` (no nodes/edges initially).

## GET /workflows/{workflow_id}

Get full workflow detail including nodes and edges.

**Response (200):**
```json
{
  "id": "uuid", "name": "Support Flow", "version": 1, "is_active": false,
  "nodes": [
    {"id": "uuid", "node_type": "start", "label": "Start", "config": {}, "position_x": 100, "position_y": 100}
  ],
  "edges": [
    {"id": "uuid", "source_node_id": "uuid1", "target_node_id": "uuid2", "source_handle": null}
  ]
}
```

## PUT /workflows/{workflow_id}

Update workflow. Supports two operations:

1. **Save graph** (when `nodes` and `edges` are both present): Calls `save_graph()` which replaces all nodes and edges atomically.
2. **Update metadata** (name, description, etc.): Updates only provided fields.

Both can happen in a single request.

**Request:**
```json
{
  "name": "Updated Flow",
  "nodes": [
    {"id": "uuid", "node_type": "llm", "label": "Classify", "config": {"llm_model": "gpt-4o"}, "position_x": 200, "position_y": 200, "width": null, "height": null}
  ],
  "edges": [
    {"id": "uuid", "source_node_id": "uuid1", "target_node_id": "uuid2", "source_handle": null, "target_handle": null, "label": null, "style": {}}
  ]
}
```

**Response (200):** Full `WorkflowResponse` with updated graph.

## DELETE /workflows/{workflow_id}

Delete a workflow.

**Response:** 204 No Content.

## POST /workflows/{workflow_id}/execute

Execute a workflow with input data. Compiles the graph to a LangGraph StateGraph and runs it.

**Request:**
```json
{ "input_data": {"user_input": "Help me with billing"}, "conversation_id": null }
```

**Response (200):**
```json
{
  "id": "run-uuid", "workflow_id": "wf-uuid", "status": "completed",
  "input_data": {"user_input": "..."}, "output_data": {"final_response": "..."},
  "node_executions": [...], "total_tokens": 450,
  "started_at": "...", "completed_at": "..."
}
```

**Errors:** 400 if workflow has no nodes.

## GET /workflows/{workflow_id}/runs

List execution history for a workflow.

**Query params:** `limit` (default 20, max 100).

**Response (200):** `WorkflowRunResponse[]`

## GET /workflows/{workflow_id}/runs/{run_id}

Get detail of a specific execution run.

**Response (200):** `WorkflowRunResponse` with full node execution logs.
