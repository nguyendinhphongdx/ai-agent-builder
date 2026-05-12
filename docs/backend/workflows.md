---
id: workflows
title: Workflow Engine
domain: backend
tags: [workflow, langgraph, stategraph, compiler, execution]
related: [table-workflows, agent-executor, table-tools]
summary: Workflow system that compiles a graph of nodes and edges into a LangGraph StateGraph, executes it, and tracks runs with per-node logging.
---

# Workflow Engine

Source: `apps/backend/app/modules/studio/workflows/` (HTTP layer) + `apps/backend/app/core/workflow_runner.py` (execution engine)

## Overview

The workflow engine allows users to define automation pipelines as directed graphs. Workflows are stored as `Workflow` + `WorkflowNode` + `WorkflowEdge` rows in the database, compiled into LangGraph `StateGraph` instances at runtime, and executed with full per-node tracing via `WorkflowRun`.

## WorkflowState

A `TypedDict` passed between nodes during execution:

| Key | Type | Purpose |
|---|---|---|
| `data` | `Any` | Primary payload passed between nodes. |
| `output` | `Any` | Final result, set by the output node. |
| `node_logs` | `list[dict]` | Execution trace for every node visited. |
| `total_tokens` | `int` | Accumulated LLM token usage. |
| `_condition_result` | `bool` | Internal flag used by condition routing. |
| `_initial_input` | `dict` | Original input data, available to human_input nodes. |

## Node Types

Each node type has a dedicated executor in `workflows/nodes/executor.py`, registered in `NODE_EXECUTORS`.

| Type | Config Fields | Behavior |
|---|---|---|
| `input` | _(none)_ | Marks the entry point. Passes `state.data` through unchanged. |
| `output` | _(none)_ | Copies `state.data` to `state.output` as the final result. |
| `llm` | `llm_provider`, `llm_model`, `system_prompt`, `temperature`, `max_tokens` | Calls an LLM with the current data as the user message. Tracks token usage. |
| `tool` | `tool_id` (UUID) | Loads a `Tool` from the database, builds it via `tool_registry`, and invokes it with current data. |
| `condition` | `condition_expression` | Evaluates a Python expression with `data` in scope. Sets `_condition_result` for routing. |
| `human_input` | `prompt_message`, `input_key`, `default_value` | In API mode, reads from `_initial_input[input_key]` or falls back to `default_value`. |

## Edge Types

| Pattern | When | Behavior |
|---|---|---|
| **Direct edge** | Source has one outgoing target | `graph.add_edge(src, tgt)` |
| **Conditional edge** | Source is a `condition` node with 2+ targets | Uses `source_handle` values (`true`/`false`) to route via `graph.add_conditional_edges()`. |
| **Terminal** | Node has no outgoing edges | `graph.add_edge(src, END)` |

## Compiler (`compiler.py`)

### `compile_workflow(workflow, db) -> (compiled_graph, start_node_id)`

1. Builds an adjacency list from nodes and edges.
2. Finds the start node (prefers `node_type="input"`, falls back to a node with no incoming edges).
3. Registers each node as an async function via `NODE_EXECUTORS[node_type]`.
4. Wires edges, using `add_conditional_edges` for condition nodes.
5. Sets the entry point and calls `graph.compile()`.

### `compile_and_run(db, workflow, user_id, input_data, conversation_id?)`

End-to-end execution wrapper:

1. Creates a `WorkflowRun` record with status `running`.
2. Compiles and invokes the graph with the initial state.
3. On success: updates the run to `completed` with `output_data`, `node_executions`, and `total_tokens`.
4. On failure: updates the run to `failed` with `error_message`.

## Service Layer (`service.py`)

CRUD operations for workflows and runs:

- `list_workflows`, `get_workflow`, `create_workflow`, `update_workflow`, `delete_workflow`
- `save_graph` -- replaces all nodes and edges atomically, increments `version`
- `create_workflow_run`, `update_workflow_run`, `get_workflow_run`, `list_workflow_runs`

## Versioning

Each call to `save_graph` increments `workflow.version`. The previous graph (nodes + edges) is deleted and replaced entirely.

## Node Execution Logging

Every node executor appends a log entry to `state["node_logs"]` with: `node_id`, `node_type`, `label`, `status`, `input_data`, `output_data`, `error`, `tokens_used`, `started_at`, `completed_at`. These logs are persisted in `WorkflowRun.node_executions` as JSONB.
