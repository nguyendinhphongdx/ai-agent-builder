---
id: frontend-feature-workflows-nodes
title: Workflow Node Types and Node Registry
domain: frontend
tags: [workflows, nodes, react-flow, registry, handles, base-node, custom-node]
related: [frontend-feature-workflows, frontend-feature-workflows-editor]
summary: Documents the node registry pattern, per-node folder structure, BaseNode and CustomNode composition, HandlePort arrays, all 18 node types across 6 categories, and the deprecation of configFields in favour of per-node panel components.
---

## Node Registry (`nodes/registry.ts`)

The registry is an explicit static map — not auto-discovered. Every node type must be imported and added by hand. This makes the full set of node types statically visible and tree-shakeable.

### NodeRegistryEntry

```typescript
interface NodeRegistryEntry {
  definition: NodeTypeDefinition;
  node: ComponentType<NodeContentProps>;   // rendered inside BaseNode on the canvas
  panel: ComponentType<PanelProps>;        // rendered in NDVModal > NodeSettingsPanel
}
```

### Registration pattern

Each node folder exports three named symbols. The registry imports them all explicitly:

```typescript
import {
  definition as llmDef,
  NodeComponent as LLMNode,
  PanelComponent as LLMPanel,
} from "./llm";

const REGISTRY: NodeRegistryEntry[] = [
  { definition: llmDef, node: LLMNode, panel: LLMPanel },
  // ...
];
```

To add a new node: create the folder, add one import block, add one line to `REGISTRY`.

### Public API

| Function | Returns | Description |
| -------- | ------- | ----------- |
| `getNodeEntry(type)` | `NodeRegistryEntry \| undefined` | O(1) lookup via `Map` |
| `getAllDefinitions()` | `NodeTypeDefinition[]` | All 18 definitions in registry order |
| `getDefinitionsByCategory(cat)` | `NodeTypeDefinition[]` | Filtered by `definition.category` |

## Per-Node Folder Structure

Each node lives in `nodes/<node-name>/`:

```text
nodes/llm/
  index.ts      — exports: definition, NodeComponent, PanelComponent
  panel.tsx     — NDV settings panel (the primary config UI)
  node.tsx      — optional canvas node content (most nodes return null)
```

`index.ts` is the only file the registry imports. `panel.tsx` is always present. `node.tsx` is only created when the node needs custom canvas content (e.g., `condition`).

### NodeComponent

Rendered as `children` inside `BaseNode` on the canvas. Most nodes return `null` (the default `BaseNode` header is sufficient). Nodes with complex canvas representations (e.g., `condition`) export a real component.

### PanelComponent

Rendered in `NodeSettingsPanel` under the "Parameters" tab via `createElement(entry.panel, { id, data })`. This is where all config editing happens — replacing the old `configFields`-driven `ConfigFieldInput` approach.

## Type Definitions (`nodes/types.ts`)

### NodeTypeDefinition

```typescript
interface NodeTypeDefinition {
  type: string;
  label: string;
  description: string;
  icon: LucideIcon;
  color: string;                    // hex, used for icon bg tint and MiniMap color
  category: NodeCategory;
  handles: {
    inputs: HandlePort[];
    outputs: HandlePort[];
  };
  canDelete?: boolean;              // default true; false for start/end/webhook_trigger
  defaultData?: () => Record<string, unknown>;
  canConnect?: (targetType: string) => boolean;
  /** @deprecated — use per-node panel.tsx instead */
  configFields?: ConfigField[];
}
```

### HandlePort

```typescript
interface HandlePort {
  id: string;
  type: "main" | "conditional";
  label?: string;                   // shown as a small label above/below the handle
  maxConnections?: number;
}
```

Handles are declared as `HandlePort[]` arrays — not numeric counts. Each port has an explicit `id` that becomes the React Flow `sourceHandle`/`targetHandle` on edges.

### NodeData (canvas node data shape)

```typescript
interface NodeData {
  nodeType: string;
  label: string;
  config: Record<string, unknown>;
  _customHandles?: boolean;         // true when the NodeComponent manages its own output handles
}
```

### configFields (deprecated)

`ConfigField[]` is still present in `NodeTypeDefinition` for backwards compatibility but is marked `@deprecated`. New nodes must not use it. Per-node `panel.tsx` components are the authoritative config UI. The old `ConfigFieldInput` component is no longer used.

## Node Categories

Defined in `nodes/types.ts` as `NODE_CATEGORIES: CategoryMeta[]`. Used by `NodePalette` for grouped display.

| Key | Label | Icon | Count |
| --- | ----- | ---- | ----- |
| `trigger` | Triggers | `Zap` | 1 |
| `ai` | AI | `Bot` | 2 |
| `integration` | Action in an app | `Globe` | 2 |
| `data` | Data transformation | `Database` | 4 |
| `logic` | Flow control | `GitBranch` | 5 |
| `flow` | Core | `Workflow` | 3 (start/end/human_input) |

## All 18 Node Types

### trigger category

#### `webhook_trigger` — Webhook Trigger

| Field | Value |
| ----- | ----- |
| Icon | `Webhook` |
| Color | `#8b5cf6` |
| `canDelete` | `false` |
| Inputs | none |
| Outputs | `default` (main) |
| Default data | `{ method: "POST", path: "/webhook" }` |

---

### ai category

#### `llm` — LLM Call

| Field | Value |
| ----- | ----- |
| Icon | `Brain` |
| Color | `#8b5cf6` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ llm_provider: "openai", llm_model: "gpt-4o" }` |

Panel fields: provider (select: openai/anthropic/ollama), api_key (text), model (select), system_prompt (textarea), prompt_template (textarea), output_variable (text).

#### `agent` — Agent

| Field | Value |
| ----- | ----- |
| Icon | `Bot` |
| Color | `#6366f1` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ output_mode: "text" }` |

Panel fields: agent_id (select, dynamically populated), output_mode (select: text/structured).

---

### integration category

#### `tool` — Tool

| Field | Value |
| ----- | ----- |
| Icon | `Wrench` |
| Color | `#f59e0b` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |

Panel fields: tool_id (select, dynamically populated), input_mapping (json), output_variable (text).

#### `http_request` — HTTP Request

| Field | Value |
| ----- | ----- |
| Icon | `Globe` |
| Color | `#8b5cf6` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ method: "GET", url: "", headers: "{}", body: "" }` |

---

### data category

#### `code` — Code

| Field | Value |
| ----- | ----- |
| Icon | `Code` |
| Color | `#64748b` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ language: "python" }` |

Panel fields: language (select: python/javascript), code (textarea), output_variable (text).

#### `knowledge_retrieval` — Knowledge Search

| Field | Value |
| ----- | ----- |
| Icon | `BookOpen` |
| Color | `#10b981` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ top_k: 5 }` |

Panel fields: query_template (text), top_k (number), output_variable (text).

#### `template` — Template

| Field | Value |
| ----- | ----- |
| Icon | `FileText` |
| Color | `#14b8a6` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ template: "", output_variable: "template_output" }` |

#### `set_variable` — Set Variable

| Field | Value |
| ----- | ----- |
| Icon | `Variable` |
| Color | `#6366f1` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ assignments: "{}" }` |

---

### logic category

#### `condition` — Condition

| Field | Value |
| ----- | ----- |
| Icon | `GitBranch` |
| Color | `#06b6d4` |
| Inputs | `default` (main) |
| Outputs | `true` (conditional), `false` (conditional) |
| `_customHandles` | `true` — NodeComponent manages its own output handles |
| Default data | `{ _customHandles: true, cases: [{ id: "true", label: "True" }, { id: "false", label: "False" }] }` |

Panel field: condition expression (text).

#### `switch` — Switch

| Field | Value |
| ----- | ----- |
| Icon | `Route` |
| Color | `#06b6d4` |
| Inputs | `default` (main) |
| Outputs | `case_0` / `case_1` / `case_2` (conditional) + `default_out` (conditional) |
| `_customHandles` | `true` |
| Default data | `{ _customHandles: true, variable: "", cases: [...] }` |

#### `filter` — Filter

| Field | Value |
| ----- | ----- |
| Icon | `Filter` |
| Color | `#10b981` |
| Inputs | `default` (main) |
| Outputs | `matched` (conditional), `unmatched` (conditional) |
| Default data | `{ expression: "" }` |

#### `merge` — Merge

| Field | Value |
| ----- | ----- |
| Icon | `Merge` |
| Color | `#f97316` |
| Inputs | `input_a` (main, label "A"), `input_b` (main, label "B") |
| Outputs | `default` (main) |
| Default data | `{ mode: "append" }` |

Note: `merge` is the only node with **multiple input handles**.

#### `loop` — Loop

| Field | Value |
| ----- | ----- |
| Icon | `Repeat` |
| Color | `#a855f7` |
| Inputs | `default` (main) |
| Outputs | `loop_body` (conditional, label "Loop body"), `done` (conditional, label "Done") |
| Default data | `{ batch_size: 1, max_iterations: 100 }` |

#### `delay` — Delay

| Field | Value |
| ----- | ----- |
| Icon | `Timer` |
| Color | `#f59e0b` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ delay_seconds: 5, unit: "seconds" }` |

---

### flow category

#### `start` — Start

| Field | Value |
| ----- | ----- |
| Icon | `Play` |
| Color | `#10b981` |
| `canDelete` | `false` |
| Inputs | none |
| Outputs | `default` (main) |
| Default data | none |

Auto-inserted when a workflow has no nodes.

#### `end` — End

| Field | Value |
| ----- | ----- |
| Icon | `Square` |
| Color | `#ef4444` |
| `canDelete` | `false` |
| Inputs | `default` (main) |
| Outputs | none |
| Default data | `{ output_variable: "final_response" }` |

#### `human_input` — Human Input

| Field | Value |
| ----- | ----- |
| Icon | `User` |
| Color | `#ec4899` |
| Inputs | `default` (main) |
| Outputs | `default` (main) |
| Default data | `{ timeout_seconds: 300 }` |

Panel fields: prompt_message (text), timeout_seconds (number).

---

## BaseNode Component (`components/custom-nodes/BaseNode.tsx`)

`BaseNode` is a presentational wrapper — not a React Flow `nodeTypes` entry directly. It is composed by `CustomNode`.

```text
[TargetHandle(s) from definition.handles.inputs]

+--[ rounded card ]-------------------+
|  [icon tinted bg]  label            |
|                    type             |
|  ---------------------------------- |
|  {children — per-node NodeComponent}|
+-------------------------------------+

[SourceHandle(s) from definition.handles.outputs]
  (skipped if _customHandles === true)
```

Props:

```typescript
interface BaseNodeProps {
  nodeId: string;
  definition: NodeTypeDefinition;
  label?: string;
  selected?: boolean;
  customHandles?: boolean;    // if true, suppresses output handles (node renders its own)
  children?: ReactNode;
}
```

Selection styling: `border-primary ring-2 ring-primary/20` when selected, `border-border` otherwise.

Icon container: `backgroundColor: ${definition.color}20` (color at ~12% opacity), icon at full color.

## CustomNode Component (`components/custom-nodes/CustomNode.tsx`)

`CustomNode` is the actual React Flow `nodeTypes` entry, registered as `"baseNode"`:

```typescript
const nodeTypes: NodeTypes = { baseNode: CustomNode };
```

It bridges React Flow's `NodeProps` to the registry:

1. Reads `data.nodeType` from node data
2. Calls `getNodeEntry(nodeType)` to get the registry entry
3. Renders `<BaseNode>` with the entry's `definition` and visual props
4. Renders `createElement(entry.node, { id, data })` as `BaseNode` children

If no registry entry is found for the `nodeType`, renders `null`.

```typescript
function CustomNodeComponent({ id, data, selected }: NodeProps) {
  const entry = getNodeEntry(data.nodeType);
  if (!entry) return null;
  return (
    <BaseNode nodeId={id} definition={entry.definition} label={data.label} selected={selected} customHandles={data._customHandles}>
      {createElement(entry.node, { id, data })}
    </BaseNode>
  );
}
export const CustomNode = memo(CustomNodeComponent);
```

## Adding a New Node Type

1. Create `nodes/<node-name>/index.ts` — export `definition`, `NodeComponent`, `PanelComponent`
2. Create `nodes/<node-name>/panel.tsx` — the NDV settings UI
3. Optionally create `nodes/<node-name>/node.tsx` if canvas content is needed
4. In `nodes/registry.ts`: add one import block and one line to `REGISTRY`
5. The node appears automatically in `NodePalette` under its declared category
