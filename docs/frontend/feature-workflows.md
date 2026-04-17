---
id: frontend-feature-workflows
title: Workflows Feature Module
domain: frontend
tags: [workflows, crud, zustand, react-flow, hooks, store]
related: [frontend-feature-workflows-editor, frontend-feature-workflows-nodes, api-workflow-endpoints]
summary: Documents the workflows feature types, service, hooks, Zustand store (workflowEditorStore), and NODE_TYPES constants.
---

# Workflows Feature

## Directory: `src/features/workflows/`

## Types (`types/index.ts`)

### Workflow

| Field       | Type                              | Description             |
|-------------|-----------------------------------|-------------------------|
| `id`        | `string`                          | UUID                    |
| `name`      | `string`                          | Workflow name           |
| `description`| `string?`                        | Optional description    |
| `agent_id`  | `string?`                         | Associated agent        |
| `version`   | `number`                          | Version counter         |
| `is_active` | `boolean`                         | Active/draft status     |
| `viewport`  | `{ x, y, zoom }`                 | Canvas viewport state   |

### WorkflowNode

`id`, `workflow_id`, `node_type: WorkflowNodeType`, `label`, `config`, `position_x`, `position_y`, `width`, `height`

### WorkflowEdge

`id`, `workflow_id`, `source_node_id`, `target_node_id`, `source_handle`, `target_handle`, `label`, `style`

### WorkflowNodeType

`"start" | "end" | "llm" | "tool" | "condition" | "human_input" | "code" | "knowledge_retrieval" | "merge"`

### WorkflowDetail

Extends `Workflow` with `nodes: WorkflowNode[]` and `edges: WorkflowEdge[]`.

### WorkflowSaveInput

Payload for saving a graph: `name?`, `description?`, `nodes[]`, `edges[]`, `viewport?`.

## Service (`services/workflowService.ts`)

| Method    | HTTP Call                          | Returns           |
|-----------|------------------------------------|--------------------|
| `list`    | `GET /workflows`                   | `Workflow[]`       |
| `getById` | `GET /workflows/${id}`             | `WorkflowDetail`   |
| `create`  | `POST /workflows`                  | `Workflow`         |
| `save`    | `PUT /workflows/${id}`             | `WorkflowDetail`   |
| `delete`  | `DELETE /workflows/${id}`          | void               |
| `execute` | `POST /workflows/${id}/execute`    | `{ run_id: string }`|

## Hooks (`hooks/useWorkflows.ts`)

| Hook                  | Type     | Behavior                                        |
|-----------------------|----------|-------------------------------------------------|
| `useWorkflows()`      | Query    | Fetches workflow list                           |
| `useWorkflow(id)`     | Query    | Fetches workflow detail with nodes/edges        |
| `useCreateWorkflow()` | Mutation | Creates workflow, navigates to `/workflows/${id}` |
| `useSaveWorkflow(id)` | Mutation | Saves graph, invalidates detail cache           |
| `useDeleteWorkflow()` | Mutation | Deletes workflow, navigates to `/workflows`     |

## Zustand Store (`stores/workflowEditorStore.ts`)

Manages React Flow state with Zustand:

### State

| Field            | Type       | Description                    |
|------------------|------------|--------------------------------|
| `nodes`          | `Node[]`   | React Flow nodes               |
| `edges`          | `Edge[]`   | React Flow edges               |
| `selectedNodeId` | `string?`  | Currently selected node        |
| `isDirty`        | `boolean`  | Whether unsaved changes exist  |

### Actions

| Action            | Description                                     |
|-------------------|-------------------------------------------------|
| `setNodes/setEdges` | Bulk replace nodes or edges                   |
| `onNodesChange`   | Applies React Flow node changes, sets dirty     |
| `onEdgesChange`   | Applies React Flow edge changes, sets dirty     |
| `onConnect`       | Adds new edge (smoothstep, animated), sets dirty|
| `addNode`         | Appends a node                                  |
| `removeNode`      | Removes node + connected edges, clears selection|
| `updateNodeData`  | Merges data into a node                         |
| `selectNode`      | Sets selected node ID                           |
| `setDirty`        | Manually set dirty flag                         |
| `reset`           | Clears all state                                |

New edges created via `onConnect` use `type: "smoothstep"`, `animated: true`, with subtle white stroke styling.

## Constants (`constants.ts`)

See `feature-workflows-nodes.md` for the full `NODE_TYPES` array and `NODE_TYPE_MAP`.
