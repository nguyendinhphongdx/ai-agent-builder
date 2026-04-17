---
id: flows-workflow-execution
title: Workflow Execution Flow
domain: flows
tags: [workflows, execution, langgraph, state-graph, compiler, nodes, runs]
related: [api-workflow-endpoints, frontend-feature-workflows, frontend-feature-workflows-nodes]
summary: End-to-end flow from saving a workflow graph through compilation to LangGraph StateGraph, executing nodes, and tracking run results.
---

# Workflow Execution Flow

## Overview

A saved workflow (nodes + edges) is compiled into a LangGraph StateGraph, executed with input data, and the run is tracked with per-node logs and token usage.

## Step-by-Step

### 1. Save Graph

Frontend editor calls `PUT /api/workflows/{id}` with nodes and edges arrays. Backend `save_graph()` atomically replaces all nodes and edges for the workflow.

### 2. Trigger Execution

User clicks "Run" or calls `POST /api/workflows/{id}/execute`:

```json
{ "input_data": {"user_input": "Help me with billing"}, "conversation_id": null }
```

### 3. Create Run Record

Backend creates a `WorkflowRun` record with `status: "running"`, `input_data`, and timestamps.

### 4. Compile Workflow

`compile_workflow(workflow, db)`:

#### 4a. Build Adjacency Graph

Converts nodes and edges into an adjacency map: `{node_id: [(target_id, source_handle), ...]}`.

#### 4b. Find Start Node

Priority order:
1. Node with `node_type == "input"` (explicit entry)
2. Node with no incoming edges (implicit entry)
3. First node (fallback)

#### 4c. Register Nodes

For each node, creates an async function wrapper that calls the appropriate `NODE_EXECUTOR` with the node's config, ID, and label.

#### 4d. Register Edges

Three edge types:
- **No outgoing edges**: connects to `END`
- **Condition node** (2+ outputs): adds conditional edges with a router function that checks `_condition_result` in state. Routes to "true" or "false" target based on `source_handle`.
- **Normal edge**: connects to first target

#### 4e. Set Entry Point and Compile

Sets the start node as entry point and calls `graph.compile()`.

### 5. Initialize State

```python
initial_state = {
    "data": input_data,
    "output": None,
    "node_logs": [],
    "total_tokens": 0,
    "_condition_result": False,
    "_initial_input": input_data,
}
```

### 6. Execute Graph

`await compiled_graph.ainvoke(initial_state)`

Each node executor receives the state and returns an updated state. The state flows through the graph following edges and conditional routing.

### 7. Node Types and Executors

Each `node_type` has a corresponding executor in `app/workflows/nodes/executor.py`:

| Node Type            | Behavior                                           |
|----------------------|----------------------------------------------------|
| `start`              | Passes state through unchanged                     |
| `end`                | Sets output from configured variable               |
| `llm`                | Calls LLM with configured model and prompt template|
| `tool`               | Executes a tool with input mapping                 |
| `condition`          | Evaluates expression, sets `_condition_result`     |
| `human_input`        | Waits for user input (with timeout)                |
| `knowledge_retrieval`| Runs pgvector similarity search                    |
| `code`               | Executes Python/JavaScript code                    |

### 8. Track Results

After execution completes:

**Success:**
```python
update_workflow_run(db, run,
    status="completed",
    output_data=final_state["output"] or final_state["data"],
    node_executions=final_state["node_logs"],
    total_tokens=final_state["total_tokens"],
    completed_at=now(),
)
```

**Failure:**
```python
update_workflow_run(db, run,
    status="failed",
    error_message=str(exception),
    completed_at=now(),
)
```

### 9. Return Run Response

API returns `WorkflowRunResponse` with status, input/output data, node execution logs, token usage, and timestamps.

## State Schema (WorkflowState)

| Field              | Type        | Description                      |
|--------------------|-------------|----------------------------------|
| `data`             | `Any`       | Data passed between nodes        |
| `output`           | `Any`       | Final output (set by end node)   |
| `node_logs`        | `list[dict]`| Per-node execution logs          |
| `total_tokens`     | `int`       | Accumulated token usage          |
| `_condition_result`| `bool`      | Condition routing flag           |
| `_initial_input`   | `dict`      | Original input (for human_input) |
