---
id: frontend-feature-workflows-editor
title: Workflow Editor View and Canvas
domain: frontend
tags: [workflows, editor, react-flow, canvas, palette, ndv, toolbar]
related: [frontend-feature-workflows, frontend-feature-workflows-nodes]
summary: Documents WorkflowEditorView layout, Canvas with React Flow setup, floating NodePalette, NDVModal (full-screen 3-panel node editor), handle-based node addition, and WorkflowToolbar controls.
---

## WorkflowEditorView (`views/WorkflowEditorView.tsx`)

### Layout

```text
+------------------------------------------+
|   [name input] [dirty dot] [tabs]  [Toolbar]  |
+------------------------------------------+
|                                          |
|   Canvas (flex-1, relative)              |
|                                  [+] btn |
|                                          |
+------------------------------------------+
     (NodePalette slides in from right)
     (NDVModal overlays full-screen)
```

Wrapped in `<ReactFlowProvider>` for React Flow context.

The view has two tabs: **editor** (Canvas + NodePalette) and **executions** (ExecutionsPanel). Tabs are toggled in the top bar.

### Data Loading

1. Fetches workflow via `useWorkflow(workflowId)`
2. Maps `WorkflowNode[]` to React Flow `Node[]`: type `"baseNode"`, position from `position_x`/`position_y`, data from `nodeType`/`label`/`config`
3. Maps `WorkflowEdge[]` to React Flow `Edge[]`: preserves `sourceHandle`/`targetHandle`/`label` if present
4. Auto-inserts a `start` node at `(250, 250)` if the workflow has no nodes
5. Calls `store.setDirty(false)` after initial load

### Save Handler

Converts React Flow nodes/edges back to API format:

- Node: extracts `nodeType`, `label`, `config` from data; `position_x`/`y` from position; `width`/`height` from `measured`
- Edge: maps `source`/`target` to `source_node_id`/`target_node_id`; preserves `source_handle`/`target_handle`/`label`
- Calls `useSaveWorkflow` mutation, resets dirty flag on success

### Run Handler

Calls `useExecuteWorkflow` with `{ message: "Hello" }`, switches to executions tab on success.

### Opening NodePalette

A floating `+` button (top-right of canvas, `z-30`) calls `store.openNodePalette()` with no context. The `NodePalette` component then slides in from the right.

## Canvas (`components/Canvas.tsx`)

### React Flow Configuration

```tsx
<ReactFlow
  nodeTypes={{ baseNode: CustomNode }}   // CustomNode, not BaseNode directly
  deleteKeyCode={null}                   // custom Delete/Backspace handler in effect
  fitView
  proOptions={{ hideAttribution: true }}
  className="bg-background"             // theme-aware, not hardcoded color
>
  <Background variant={BackgroundVariant.Dots} gap={16} size={1.5}
    color={isDark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)"} />
  <MiniMap
    nodeColor={(node) => getNodeEntry(node.data?.nodeType)?.definition.color ?? fallback}
    pannable zoomable
    style={{ width: 160, height: 100 }}
  />
</ReactFlow>
```

Theme is resolved via `useTheme()` from `next-themes`. MiniMap node colors come from each node's definition in the registry.

### Interaction Model

| Interaction | Effect |
| ----------- | ------ |
| Single click on node | `selectNode(id)` — highlights node on canvas |
| Double click on node | `selectNode(id)` + `editNode(id)` — opens NDVModal |
| Click empty pane | `selectNode(null)` + `editNode(null)` — deselects and closes NDV |
| Drag node type from palette | `handleDrop` — converts screen coords to flow position, calls `addNode` |
| `Escape` key | Deselects, closes NDV, closes NodePalette |
| `Delete`/`Backspace` key | `removeNode(selectedNodeId)` if a node is selected |

### Drag-and-Drop

- `handleDrop`: reads `nodeType` from `dataTransfer`, converts screen coords via `reactFlowRef.current.screenToFlowPosition`, calls `addNode`
- `handleDragOver`: sets `dropEffect: "move"`
- Uses a `useRef<ReactFlowInstance>` captured in `onInit`

## NodePalette (`components/NodePalette.tsx`)

A **floating right-side panel** (320px wide), not a permanent sidebar. Controlled by `store.nodePaletteOpen`.

### Trigger points

- Floating `+` button in the canvas overlay → `store.openNodePalette()` (no context)
- `HandlePlus` button on an unconnected source handle → `store.openNodePalette({ sourceNodeId, sourceHandleId })` (with context)

When opened with context, the header shows **"What happens next?"** instead of **"Add Node"**.

### UI Structure

```text
+-------- NodePalette (w-80, slides from right) --------+
|  [← back?]  [Title]                          [X]      |
|  [Search input]                                        |
|  --------------------------------------------------------|
|  Category list (default):                              |
|    [Icon] Triggers        3  >                         |
|    [Icon] AI              2  >                         |
|    [Icon] Action in app   2  >                         |
|    [Icon] Data transform  4  >                         |
|    [Icon] Flow control    5  >                         |
|    [Icon] Core            3  >                         |
|                                                        |
|  (or drill-down: node list for selected category)      |
|  (or flat search results if search is non-empty)       |
+--------------------------------------------------------+
```

An invisible backdrop div covers the canvas and closes the palette on click.

### Category drill-down

- Default view: 6 categories from `NODE_CATEGORIES` with item count and `>` chevron
- Click a category → sets `activeCategory`, shows filtered node list with a `<` back button
- Search overrides category view — shows flat results across all categories
- Escape with category active → goes back to category list; Escape at top level → closes

### Adding a node

1. User clicks a node entry (or drags it to the canvas)
2. `handleAddNode(type)`:
   - Computes position: if `addNodeContext` exists, places the new node 80px to the right of the source node; otherwise uses a random center position
   - Calls `addNode(...)` with type `"baseNode"` and `defaultData` from registry
   - If `addNodeContext` exists, calls `onConnect(...)` to auto-create an edge from the source handle to the new node's first input handle
3. Calls `closeNodePalette()`

Nodes in the list are also **draggable** — `onDragStart` sets `dataTransfer` and closes the palette.

## NDVModal (`components/ndv/NDVModal.tsx`)

Replaces the old NodeInspector. Full-screen modal (inset 16px all sides) that opens when `store.editingNodeId` is set (triggered by double-clicking a node).

### Panel layout

```text
+-----------------------------------------------+
|  NDVHeader (node icon, name, type, close btn)  |
+---------------+--+-------------+--+-----------+
|  INPUT panel  |‖| Settings     |‖| OUTPUT     |
|  (40% default)|‖| panel        |‖| panel      |
|               |‖| (flex-1)     |‖| (40% def.) |
+---------------+--+-------------+--+-----------+
```

The two vertical drag handles (`‖`) are resizable via mouse drag. Minimum panel width: 200px. Ratios reset to defaults (40/20/40) each time a new node is opened.

### Sub-components

| Component | File | Purpose |
| --------- | ---- | ------- |
| `NDVHeader` | `ndv/NDVHeader.tsx` | Node icon, label, type name, close button |
| `InputPanel` | `ndv/InputPanel.tsx` | Shows input data fed to the node (run context) |
| `NodeSettingsPanel` | `ndv/NodeSettingsPanel.tsx` | Parameters + Settings tabs |
| `OutputPanel` | `ndv/OutputPanel.tsx` | Shows output data from the node (run context) |

### NodeSettingsPanel tabs

- **Parameters**: renders `createElement(entry.panel, { id, data })` — the per-node `panel.tsx` from the registry
- **Settings**: editable node label (`Input`), about description, and Delete Node button (hidden if `canDelete === false`)

### Accessibility

`DialogPrimitive.Title` with `className="sr-only"` provides a screen-reader title: `"[label] — Node Editor"`.

## Handles (`components/handles/`)

### TargetHandle

Plain `<Handle type="target" position={Position.Top}>` with optional label. No interactive extras.

### SourceHandle

```text
[Handle] (Position.Bottom by default)
[HandlePlus button] — shown only when handle has no connected edge
```

`HandlePlus` is a small `+` button rendered below the handle. Clicking it calls `store.openNodePalette({ sourceNodeId, sourceHandleId })`.

### HandlePlus (`handles/HandlePlus.tsx`)

A 20×20px icon button (`Plus` icon) positioned absolutely below the source handle. Stops event propagation to prevent node selection on click.

## Zustand Store (`stores/workflowEditorStore.ts`)

Key state relevant to the editor UI:

| Field | Type | Purpose |
| ----- | ---- | ------- |
| `selectedNodeId` | `string \| null` | Which node is highlighted on canvas |
| `editingNodeId` | `string \| null` | Which node has NDVModal open |
| `nodePaletteOpen` | `boolean` | Whether NodePalette panel is visible |
| `addNodeContext` | `AddNodeContext \| null` | Source handle context for palette-triggered connections |

Key actions:

| Action | Effect |
| ------ | ------ |
| `selectNode(id)` | Sets `selectedNodeId` |
| `editNode(id)` | Sets `editingNodeId`, opens NDVModal |
| `openNodePalette(context?)` | Sets `nodePaletteOpen: true`, stores optional `addNodeContext` |
| `closeNodePalette()` | Sets `nodePaletteOpen: false`, clears `addNodeContext` |
| `removeNode(id)` | Removes node + connected edges; guards against `canDelete: false` |
| `updateNodeData(id, data)` | Merges partial data into node, marks dirty |

## WorkflowToolbar (`components/WorkflowToolbar.tsx`)

Rendered inside the top bar row alongside the name input and tabs. Contains:

- Zoom controls: ZoomOut, FitView, ZoomIn (via `useReactFlow()`)
- **Run** button — calls `onRun` prop
- **Save** button — disabled when not dirty or saving, shows spinner when `isSaving`
