---
id: frontend-workflow-editor-architecture-research
title: Workflow Editor Architecture Research (n8n & Dify)
domain: frontend
tags: [workflows, architecture, research, n8n, dify, design-patterns]
related: [frontend-feature-workflows-editor, frontend-feature-workflows-nodes]
summary: Research into n8n and Dify workflow editor architectures — design patterns, folder structures, node systems, handle/output patterns, and proposed architecture for AgentForge.
---

# Workflow Editor Architecture Research

Research from **n8n** (Vue + VueFlow) and **Dify** (React + ReactFlow) to inform AgentForge's workflow editor redesign.

---

## 1. Dify Architecture (React + ReactFlow)

### 1.1 Folder Structure

```
web/app/components/workflow/
├── block-selector/           # Node palette (search, tabs, categories)
│   ├── index.tsx             # Main block selector component
│   ├── main.tsx              # Core selector UI
│   ├── blocks.tsx            # Built-in blocks list
│   ├── tools.tsx             # External tools list
│   ├── tabs.tsx              # Tab navigation (Start, Blocks, Tools, Sources)
│   ├── hooks.ts              # Selector-specific hooks
│   ├── types.ts              # BlockClassificationEnum, TabsEnum, etc.
│   └── constants.tsx         # Block classification definitions
├── nodes/
│   ├── _base/                # Shared base components for ALL nodes
│   │   ├── node.tsx          # BaseNode wrapper (icon, title, handles, status)
│   │   ├── node-sections.tsx # Reusable header/body/description sections
│   │   ├── types.ts          # Base node type definitions
│   │   └── components/
│   │       ├── node-handle/      # Source/Target handle components
│   │       ├── node-control/     # Node action buttons
│   │       ├── node-resizer/     # Resize handles
│   │       ├── error-handle/     # Error handling UI
│   │       ├── retry/            # Retry config UI
│   │       ├── workflow-panel/   # Base panel wrapper
│   │       └── ...
│   ├── components.ts         # ★ REGISTRY: NodeComponentMap + PanelComponentMap
│   ├── index.tsx             # CustomNode + Panel entry points
│   ├── constants.ts          # Shared node constants
│   ├── utils.ts              # Shared node utilities
│   ├── start/                # Each node type is a folder:
│   │   ├── node.tsx          #   Canvas rendering
│   │   ├── panel.tsx         #   Config panel
│   │   ├── types.ts          #   TypeScript types
│   │   └── use-config.ts     #   Config logic hook
│   ├── end/
│   ├── llm/
│   ├── if-else/              # Condition node with dynamic outputs
│   ├── code/
│   ├── tool/
│   ├── agent/
│   ├── iteration/            # Container node (children inside)
│   ├── loop/
│   ├── http/
│   ├── knowledge-retrieval/
│   ├── question-classifier/
│   └── ...25+ node types
├── panel/                    # Right-side panel system
├── store/                    # Zustand store
├── hooks/                    # Editor-wide hooks
├── hooks-store/              # Hook-based stores
├── constants/                # Editor constants
├── constants.ts              # Global constants (NODE_WIDTH, positions)
├── types.ts                  # ★ Core types: BlockEnum, CommonNodeType, Edge, etc.
├── context.tsx               # React context for workflow
├── custom-edge.tsx           # Custom edge rendering
├── custom-connection-line.tsx
├── index.tsx                 # Main workflow editor component
└── utils/                    # Shared utilities
```

### 1.2 Key Design Patterns

#### Pattern 1: Component Map Registry

```typescript
// nodes/components.ts — THE core pattern
export const NodeComponentMap: Record<string, ComponentType> = {
  [BlockEnum.Start]: StartNode,
  [BlockEnum.IfElse]: IfElseNode,
  [BlockEnum.LLM]: LLMNode,
  // ...each node type maps to its component
}

export const PanelComponentMap: Record<string, ComponentType> = {
  [BlockEnum.Start]: StartPanel,
  [BlockEnum.IfElse]: IfElsePanel,
  // ...each node type maps to its config panel
}
```

**To add a new node type:**
1. Create folder `nodes/my-node/` with `node.tsx`, `panel.tsx`, `types.ts`
2. Add to `BlockEnum` in `types.ts`
3. Register in `NodeComponentMap` and `PanelComponentMap`

#### Pattern 2: BaseNode + Composition

```tsx
// nodes/index.tsx — Single ReactFlow nodeType
const CustomNode = (props: NodeProps) => {
  const NodeComponent = NodeComponentMap[props.data.type]
  return (
    <BaseNode id={props.id} data={props.data}>
      <NodeComponent />    {/* Type-specific inner content */}
    </BaseNode>
  )
}
```

- `BaseNode` handles: icon, title, status, handles, resize, error display
- Child `NodeComponent` only renders type-specific content (conditions, fields preview, etc.)

#### Pattern 3: Dynamic Handles per Node Type

```tsx
// nodes/if-else/node.tsx — Handles inline with content
const IfElseNode = (props) => {
  const { cases } = props.data
  return (
    <div>
      {cases.map((caseItem, index) => (
        <div key={caseItem.case_id}>
          <div>{index === 0 ? 'IF' : 'ELIF'}</div>
          {/* Handle positioned INSIDE the node content */}
          <NodeSourceHandle
            {...props}
            handleId={caseItem.case_id}    // Dynamic handle per case
            handleClassName="..."
          />
        </div>
      ))}
      {/* ELSE always present */}
      <NodeSourceHandle handleId="false" />
    </div>
  )
}
```

Key insight: **Handles are placed BY the node component itself**, not by the base wrapper. Each node type controls its own output handles.

#### Pattern 4: Per-Node Config Hook

```typescript
// nodes/if-else/use-config.ts
export function useConfig(id: string, data: IfElseNodeType) {
  const handleAddCase = useCallback(...)
  const handleRemoveCase = useCallback(...)
  const handleUpdateCondition = useCallback(...)
  return { handleAddCase, handleRemoveCase, handleUpdateCondition }
}
```

Each node type encapsulates its own config logic in a custom hook.

#### Pattern 5: CommonNodeType with Generics

```typescript
// types.ts
export type CommonNodeType<T = {}> = {
  title: string
  desc: string
  type: BlockEnum
  _connectedSourceHandleIds?: string[]
  _targetBranches?: Branch[]     // ★ Dynamic output branches
  _runningStatus?: NodeRunningStatus
  // ...runtime state
} & T   // ★ Node-specific data merged in

// Per-node types extend this:
export type IfElseNodeType = CommonNodeType & {
  cases: CaseItem[]
}
```

### 1.3 Block Selector (Node Palette)

- Tabbed: Start | Blocks | Tools | Sources
- Search with fuzzy matching
- Categories: `BlockClassificationEnum` (QuestionUnderstand, Logic, Transform, Utilities)
- Triggered from handle "+" button or toolbar
- Each tab has its own component for rendering items

---

## 2. n8n Architecture (Vue + VueFlow)

### 2.1 Folder Structure

```
packages/frontend/editor-ui/src/
├── app/
│   ├── stores/
│   │   └── canvas.store.ts           # Canvas-level state
│   ├── constants/                    # App-wide constants
│   └── utils/
│       ├── nodes/                    # Node utility functions
│       └── nodeTypes/                # Node type utilities
├── features/
│   ├── workflows/
│   │   └── canvas/
│   │       ├── canvas.types.ts       # ★ Core types (CanvasNodeData, ports, render)
│   │       ├── canvas.utils.ts       # Canvas utilities
│   │       ├── canvas.eventBus.ts    # Event communication
│   │       ├── components/
│   │       │   ├── Canvas.vue        # VueFlow wrapper
│   │       │   ├── WorkflowCanvas.vue # Business logic wrapper
│   │       │   └── elements/
│   │       │       ├── nodes/
│   │       │       │   ├── CanvasNode.vue         # Node wrapper
│   │       │       │   ├── CanvasNodeRenderer.vue  # ★ Render type router
│   │       │       │   ├── CanvasNodeToolbar.vue
│   │       │       │   └── render-types/
│   │       │       │       ├── CanvasNodeDefault.vue
│   │       │       │       ├── CanvasNodeStickyNote.vue
│   │       │       │       ├── CanvasNodeAddNodes.vue    # "+" placeholder node
│   │       │       │       ├── CanvasNodeChoicePrompt.vue
│   │       │       │       └── parts/                    # Shared sub-components
│   │       │       ├── handles/
│   │       │       │   ├── CanvasHandleRenderer.vue      # Handle router
│   │       │       │   └── render-types/
│   │       │       │       ├── CanvasHandleMainInput.vue
│   │       │       │       ├── CanvasHandleMainOutput.vue  # ★ Has "+" button
│   │       │       │       ├── CanvasHandleNonMainInput.vue
│   │       │       │       ├── CanvasHandleNonMainOutput.vue
│   │       │       │       └── parts/
│   │       │       │           ├── CanvasHandleDot.vue
│   │       │       │           ├── CanvasHandleDiamond.vue
│   │       │       │           └── CanvasHandlePlus.vue   # ★ Plus button
│   │       │       ├── edges/
│   │       │       │   ├── CanvasEdge.vue
│   │       │       │   ├── CanvasEdgeToolbar.vue
│   │       │       │   └── CanvasConnectionLine.vue
│   │       │       └── background/
│   │       │           └── CanvasBackground.vue
│   │       └── composables/
│   │           ├── useCanvas.ts
│   │           ├── useCanvasNode.ts
│   │           ├── useCanvasNodeHandle.ts
│   │           ├── useCanvasMapping.ts       # Maps n8n data → VueFlow
│   │           ├── useCanvasLayout.ts
│   │           └── useCanvasTraversal.ts
│   ├── shared/
│   │   └── nodeCreator/              # ★ Node palette/selector
│   │       ├── components/
│   │       │   ├── NodeCreator.vue   # Main creator component
│   │       │   ├── Modes/
│   │       │   │   ├── NodesMode.vue
│   │       │   │   └── ActionsMode.vue
│   │       │   ├── Panel/
│   │       │   │   ├── NodesListPanel.vue
│   │       │   │   ├── SearchBar.vue
│   │       │   │   └── NoResults.vue
│   │       │   ├── ItemTypes/
│   │       │   │   ├── NodeItem.vue
│   │       │   │   ├── CategoryItem.vue
│   │       │   │   ├── ActionItem.vue
│   │       │   │   └── SubcategoryItem.vue
│   │       │   └── Renderers/
│   │       │       ├── ItemsRenderer.vue
│   │       │       └── CategorizedItemsRenderer.vue
│   │       ├── composables/
│   │       │   ├── useActions.ts
│   │       │   ├── useKeyboardNavigation.ts
│   │       │   └── useViewStacks.ts
│   │       ├── nodeCreator.store.ts
│   │       ├── nodeCreator.utils.ts
│   │       └── views/
│   │           ├── NodeCreation.vue
│   │           └── viewsData.ts
│   └── ndv/                          # Node Detail View (config panel)
│       ├── panel/
│       ├── parameters/
│       ├── runData/
│       ├── settings/
│       └── shared/
```

### 2.2 Key Design Patterns

#### Pattern 1: Render Type Enum + Renderer Router

```typescript
// canvas.types.ts
export const enum CanvasNodeRenderType {
  Default = 'default',
  StickyNote = 'n8n-nodes-base.stickyNote',
  AddNodes = 'n8n-nodes-internal.addNodes',
  ChoicePrompt = 'n8n-nodes-internal.choicePrompt',
}
```

```vue
<!-- CanvasNodeRenderer.vue — Routes to correct visual component -->
<script setup>
const Render = () => {
  switch (node.data.render.type) {
    case CanvasNodeRenderType.StickyNote: return h(CanvasNodeStickyNote)
    case CanvasNodeRenderType.AddNodes: return h(CanvasNodeAddNodes)
    default: return h(CanvasNodeDefault)
  }
}
</script>
```

#### Pattern 2: Rich Connection Port Types

```typescript
// canvas.types.ts
export type CanvasConnectionPort = {
  node?: string
  type: NodeConnectionType      // 'main' | 'ai_tool' | 'ai_memory' | etc.
  index: number
  required?: boolean
  maxConnections?: number
  label?: string
}

export interface CanvasNodeData {
  inputs: CanvasConnectionPort[]    // ★ Array of typed ports
  outputs: CanvasConnectionPort[]   // ★ Array of typed ports
  render: CanvasNodeDefaultRender | CanvasNodeStickyNoteRender | ...
}
```

Key insight: inputs/outputs are **arrays of port objects** with type, index, label, max connections — not just counts.

#### Pattern 3: Plus Button on Output Handles

```vue
<!-- CanvasHandleMainOutput.vue -->
<template>
  <div>
    <CanvasHandleDot />
    <!-- Plus only shows when NOT connected and NOT read-only -->
    <CanvasHandlePlus
      v-if="!isConnected && !isReadOnly"
      @click:plus="onClickAdd"     <!-- Emits 'add' event -->
    />
  </div>
</template>
```

The "+" button:
- Only visible on **unconnected** output handles
- Clicking opens the Node Creator panel
- The panel knows which handle triggered it, so it can auto-connect

#### Pattern 4: Composables for Logic Reuse

```typescript
// composables/useCanvasNode.ts — Shared node logic
export function useCanvasNode() {
  const data = inject(CanvasNodeKey)
  // Returns computed properties, methods
  return { render, runDataOutputMap, ... }
}

// composables/useCanvasNodeHandle.ts — Shared handle logic
export function useCanvasNodeHandle() {
  const data = inject(CanvasNodeHandleKey)
  return { label, isConnected, isConnecting, runData, ... }
}
```

#### Pattern 5: Event Bus for Canvas Communication

```typescript
// canvas.eventBus.ts
type CanvasEventBusEvents = {
  fitView: never
  'nodes:select': { ids: string[] }
  'create:sticky': never
  tidyUp: { source: string }
}
```

Used for cross-component communication without prop drilling.

#### Pattern 6: "AddNodes" Virtual Node

n8n creates a special virtual node of type `CanvasNodeRenderType.AddNodes` that renders as a "+" button directly on the canvas. This acts as a persistent entry point for adding the first node.

---

## 3. Comparison Summary

| Aspect | Dify | n8n |
|--------|------|-----|
| **Framework** | React + ReactFlow | Vue + VueFlow |
| **Node registration** | `ComponentMap` record | Render type enum + switch |
| **Node rendering** | BaseNode wraps type-specific child | CanvasNode → CanvasNodeRenderer → render-type |
| **Config panel** | PanelComponentMap → per-node panel | Separate NDV (Node Detail View) feature |
| **Handles** | Node component places its own handles | Handle renderer with render-type sub-components |
| **Multi-output** | `_targetBranches` + per-case `handleId` | `outputs: CanvasConnectionPort[]` array |
| **"+" button** | On handle connection | On unconnected output handle |
| **Node palette** | block-selector/ with tabs + search | nodeCreator/ with modes + search |
| **State** | Zustand store | Pinia store |
| **Logic reuse** | Custom hooks (`use-config.ts`) | Composables (`useCanvasNode.ts`) |

---

## 4. Proposed Architecture for AgentForge (v2 — revised)

> **Design goal:** Adding a new node type = create 1 folder + edit 1 file. Zero changes to core components.

### 4.1 Weaknesses of v1 Proposal (fixed below)

| Problem | Why it's bad | Fix |
|---------|-------------|-----|
| `registerNode()` side-effect imports | Tree-shaking can drop them; import order is implicit; debugging is hard | **Explicit map** like Dify — one `registry.ts` file with all imports |
| `WorkflowNodeType` string union | Every new node requires editing the union type | **String literal type** — registry is the source of truth, no union to maintain |
| `ICON_MAP` centralized | Icons duplicated in BaseNode + NodePalette | **Icon in definition** — each node declares its Lucide icon component directly |
| Missing: connection rules | Any node can connect to any node | **`canConnect` in definition** — optional validation function |
| Missing: default data | No initial config when creating node | **`defaultData` in definition** — factory function for initial config |
| Missing: palette context | "+" on handle doesn't know source node/handle | **Store state** `addNodeContext: { sourceNodeId, sourceHandleId } | null` |

### 4.2 Target Folder Structure

```
features/workflows/
├── components/
│   ├── canvas/
│   │   ├── Canvas.tsx                    # ReactFlow wrapper
│   │   ├── CanvasControls.tsx            # Zoom, fit-view, minimap controls
│   │   └── CanvasBackground.tsx          # Background pattern
│   ├── edges/
│   │   ├── CustomEdge.tsx                # Styled edge with labels
│   │   └── ConnectionLine.tsx            # Line while dragging
│   ├── handles/
│   │   ├── SourceHandle.tsx              # Output handle with "+" button
│   │   ├── TargetHandle.tsx              # Input handle
│   │   └── HandlePlus.tsx                # "+" button component
│   ├── node-palette/
│   │   ├── NodePalette.tsx               # Slide-in panel
│   │   ├── NodePaletteSearch.tsx         # Search input
│   │   ├── NodePaletteCategory.tsx       # Category grouping
│   │   └── NodePaletteItem.tsx           # Single node item
│   ├── node-inspector/
│   │   ├── NodeInspector.tsx             # Sheet wrapper — routes to per-node panel
│   │   ├── NodeInspectorHeader.tsx       # Icon + title + type
│   │   └── fields/                       # Reusable config field components
│   │       ├── TextField.tsx
│   │       ├── TextareaField.tsx
│   │       ├── SelectField.tsx
│   │       ├── NumberField.tsx
│   │       └── JsonField.tsx
│   ├── toolbar/
│   │   └── WorkflowToolbar.tsx
│   └── executions/
│       └── ExecutionsPanel.tsx
├── nodes/
│   ├── _base/                            # Shared base node wrapper
│   │   ├── BaseNode.tsx                  # Wrapper: icon, title, selection, default handles
│   │   └── types.ts                      # BaseNodeProps, PanelProps interfaces
│   ├── registry.ts                       # ★ SINGLE FILE: explicit map (Dify-style)
│   ├── types.ts                          # HandlePort, NodeTypeDefinition, NodeCategory
│   ├── start/
│   │   ├── index.ts                      # Exports { definition, NodeComponent, PanelComponent }
│   │   ├── node.tsx                      # Canvas body content
│   │   └── panel.tsx                     # Config panel
│   ├── end/
│   ├── llm/
│   │   ├── index.ts
│   │   ├── node.tsx
│   │   ├── panel.tsx
│   │   ├── types.ts                      # LLMNodeData
│   │   └── use-config.ts                 # Config logic hook
│   ├── condition/
│   │   ├── index.ts
│   │   ├── node.tsx                      # ★ Renders per-case handles dynamically
│   │   ├── panel.tsx                     # Add/remove/edit cases
│   │   ├── types.ts                      # CaseItem, Condition
│   │   └── use-config.ts
│   ├── tool/
│   ├── code/
│   ├── human-input/
│   ├── knowledge-retrieval/
│   └── agent/
├── stores/
│   └── workflowEditorStore.ts
├── hooks/
│   ├── useWorkflows.ts                   # CRUD React Query hooks
│   └── useNodeConfig.ts                  # Shared: updateConfig helper
├── services/
│   └── workflowService.ts
├── types/
│   └── index.ts
├── views/
│   ├── WorkflowEditorView.tsx
│   └── WorkflowListView.tsx
└── index.ts
```

### 4.3 Core Design Patterns

#### Pattern 1: Explicit Registry Map (Dify-style, no side-effects)

```typescript
// nodes/types.ts
import type { ComponentType } from "react"
import type { LucideIcon } from "lucide-react"

export type NodeCategory = "flow" | "ai" | "data" | "logic" | "integration"

export interface HandlePort {
  id: string                           // Unique handle identifier
  type: "main" | "conditional"         // Port type
  label?: string                       // e.g. "true", "false"
  maxConnections?: number              // Default: unlimited
}

export interface NodeTypeDefinition {
  type: string                         // ★ Plain string, no union to maintain
  label: string
  description: string
  icon: LucideIcon                     // ★ Direct component ref, no ICON_MAP
  color: string
  category: NodeCategory
  handles: {
    inputs: HandlePort[]
    outputs: HandlePort[]              // Static defaults; node component can override
  }
  defaultData?: () => Record<string, unknown>  // ★ Initial config on creation
  canConnect?: (target: string) => boolean     // ★ Connection validation
}

export interface NodeRegistryEntry {
  definition: NodeTypeDefinition
  node: ComponentType<NodeContentProps>    // What renders INSIDE BaseNode
  panel: ComponentType<PanelProps>         // What renders in NodeInspector
}

export interface NodeContentProps {
  id: string
  data: { nodeType: string; label: string; config: Record<string, unknown> }
}

export interface PanelProps {
  id: string
  data: { nodeType: string; label: string; config: Record<string, unknown> }
}
```

```typescript
// nodes/registry.ts — ★ ONE file, explicit imports, no side-effects
import type { NodeRegistryEntry, NodeTypeDefinition } from "./types"

// Import each node's exports
import { definition as startDef, NodeComponent as StartNode, PanelComponent as StartPanel } from "./start"
import { definition as endDef, NodeComponent as EndNode, PanelComponent as EndPanel } from "./end"
import { definition as llmDef, NodeComponent as LLMNode, PanelComponent as LLMPanel } from "./llm"
import { definition as conditionDef, NodeComponent as ConditionNode, PanelComponent as ConditionPanel } from "./condition"
import { definition as toolDef, NodeComponent as ToolNode, PanelComponent as ToolPanel } from "./tool"
import { definition as codeDef, NodeComponent as CodeNode, PanelComponent as CodePanel } from "./code"
import { definition as humanInputDef, NodeComponent as HumanInputNode, PanelComponent as HumanInputPanel } from "./human-input"
import { definition as knowledgeDef, NodeComponent as KnowledgeNode, PanelComponent as KnowledgePanel } from "./knowledge-retrieval"
import { definition as agentDef, NodeComponent as AgentNode, PanelComponent as AgentPanel } from "./agent"

// ★ The registry — add new nodes HERE (1 line)
const REGISTRY: NodeRegistryEntry[] = [
  { definition: startDef, node: StartNode, panel: StartPanel },
  { definition: endDef, node: EndNode, panel: EndPanel },
  { definition: llmDef, node: LLMNode, panel: LLMPanel },
  { definition: conditionDef, node: ConditionNode, panel: ConditionPanel },
  { definition: toolDef, node: ToolNode, panel: ToolPanel },
  { definition: codeDef, node: CodeNode, panel: CodePanel },
  { definition: humanInputDef, node: HumanInputNode, panel: HumanInputPanel },
  { definition: knowledgeDef, node: KnowledgeNode, panel: KnowledgePanel },
  { definition: agentDef, node: AgentNode, panel: AgentPanel },
]

// Lookup maps (computed once)
const byType = new Map(REGISTRY.map(e => [e.definition.type, e]))

// Public API
export function getNodeEntry(type: string): NodeRegistryEntry | undefined {
  return byType.get(type)
}

export function getAllDefinitions(): NodeTypeDefinition[] {
  return REGISTRY.map(e => e.definition)
}

export function getDefinitionsByCategory(category: string): NodeTypeDefinition[] {
  return REGISTRY.filter(e => e.definition.category === category).map(e => e.definition)
}
```

```typescript
// nodes/start/index.ts — Each node exports 3 things
import { Play } from "lucide-react"
import type { NodeTypeDefinition } from "../types"
import StartNodeComponent from "./node"
import StartPanelComponent from "./panel"

export const definition: NodeTypeDefinition = {
  type: "start",
  label: "Start",
  description: "Entry point of the workflow",
  icon: Play,                          // ★ Direct Lucide component
  color: "#10b981",
  category: "flow",
  handles: {
    inputs: [],
    outputs: [{ id: "default", type: "main" }],
  },
}

export const NodeComponent = StartNodeComponent
export const PanelComponent = StartPanelComponent
```

**Why this is better than side-effect `registerNode()`:**
- No tree-shaking risk — explicit imports are always included
- One obvious place to see all registered nodes
- Import errors caught at build time
- Easy to temporarily disable a node (comment out 1 line)

#### Pattern 2: BaseNode + Composition

```tsx
// nodes/_base/BaseNode.tsx
const BaseNode = ({ id, data, selected, children }: BaseNodeProps) => {
  const entry = getNodeEntry(data.nodeType)
  if (!entry) return null
  const { definition } = entry
  const Icon = definition.icon             // ★ No ICON_MAP lookup

  return (
    <>
      {/* Input handles from definition */}
      {definition.handles.inputs.map(port => (
        <TargetHandle key={port.id} handleId={port.id} label={port.label} />
      ))}

      <div className={cn("node-card", selected && "node-card--selected")}>
        <div className="node-header">
          <div className="node-icon" style={{ backgroundColor: `${definition.color}15` }}>
            <Icon className="h-3.5 w-3.5" style={{ color: definition.color }} />
          </div>
          <div>
            <span className="node-label">{data.label || definition.label}</span>
            <span className="node-type">{definition.type}</span>
          </div>
        </div>

        {/* Type-specific content rendered by child */}
        {children && <div className="node-body">{children}</div>}
      </div>

      {/* Default output handles — only if node component doesn't manage its own */}
      {!data._customHandles && definition.handles.outputs.map(port => (
        <SourceHandle key={port.id} handleId={port.id} label={port.label} />
      ))}
    </>
  )
}
```

```tsx
// Entry point: single ReactFlow nodeType
// nodes/index.tsx (registered in Canvas as nodeTypes={{ custom: CustomNode }})
const CustomNode = memo(({ id, data, selected }: ReactFlowNodeProps) => {
  const entry = getNodeEntry(data.nodeType)
  if (!entry) return null
  const NodeContent = entry.node

  return (
    <BaseNode id={id} data={data} selected={selected}>
      <NodeContent id={id} data={data} />
    </BaseNode>
  )
})
```

#### Pattern 3: Dynamic Handles (Condition Node)

Condition nodes set `data._customHandles = true` so BaseNode skips default output handles.
The node component renders its own handles based on config:

```tsx
// nodes/condition/node.tsx
const ConditionNode = ({ id, data }: NodeContentProps) => {
  const cases: CaseItem[] = data.config.cases || [
    { id: "case_true", label: "True" },
    { id: "case_false", label: "False" },
  ]

  // Mark that this node manages its own handles
  useEffect(() => {
    updateNodeData(id, { _customHandles: true })
  }, [])

  return (
    <div className="condition-branches">
      {cases.map((c, i) => (
        <div key={c.id} className="branch-row">
          <span className="branch-label">{c.label || `Case ${i + 1}`}</span>
          <SourceHandle handleId={c.id} label={c.label} position="right" />
        </div>
      ))}
      <div className="branch-row">
        <span className="branch-label">ELSE</span>
        <SourceHandle handleId="else" label="Else" position="right" />
      </div>
    </div>
  )
}
```

#### Pattern 4: "+" on Handles with Context

```tsx
// components/handles/SourceHandle.tsx
const SourceHandle = ({ handleId, label, nodeId }: SourceHandleProps) => {
  const edges = useWorkflowEditorStore(s => s.edges)
  const openPalette = useWorkflowEditorStore(s => s.openNodePalette)

  const isConnected = edges.some(
    e => e.source === nodeId && e.sourceHandle === handleId
  )

  return (
    <div className="handle-wrapper">
      <Handle type="source" id={handleId} position={Position.Bottom} />
      {label && <span className="handle-label">{label}</span>}
      {!isConnected && (
        <button
          className="handle-plus"
          onClick={() => openPalette({
            sourceNodeId: nodeId,       // ★ Context: which node/handle
            sourceHandleId: handleId,   //    triggered the palette
          })}
        >
          <Plus className="h-3 w-3" />
        </button>
      )}
    </div>
  )
}
```

Store additions:

```typescript
// In workflowEditorStore
interface WorkflowEditorState {
  // ...existing state
  nodePaletteOpen: boolean
  addNodeContext: { sourceNodeId: string; sourceHandleId: string } | null

  openNodePalette: (context?: { sourceNodeId: string; sourceHandleId: string }) => void
  closeNodePalette: () => void
}
```

When a node is selected from the palette with context:
1. Create the new node positioned below/right of the source node
2. Auto-create an edge from `sourceNodeId:sourceHandleId` → new node's first input handle

#### Pattern 5: Per-Node Config Panel

```tsx
// nodes/llm/panel.tsx — Full control over UI
const LLMPanel = ({ id, data }: PanelProps) => {
  const { updateConfig } = useNodeConfig(id)
  const config = data.config as LLMConfig

  return (
    <div className="space-y-4">
      <SelectField
        label="Provider"
        value={config.llm_provider}
        options={PROVIDER_OPTIONS}
        onChange={(v) => updateConfig("llm_provider", v)}
      />
      <SelectField
        label="Model"
        value={config.llm_model}
        options={getModelsForProvider(config.llm_provider)}  // ★ Dynamic based on provider
        onChange={(v) => updateConfig("llm_model", v)}
      />
      <TextareaField
        label="System Prompt"
        value={config.system_prompt}
        onChange={(v) => updateConfig("system_prompt", v)}
      />
    </div>
  )
}
```

NodeInspector routes to the correct panel via registry:

```tsx
// components/node-inspector/NodeInspector.tsx
const NodeInspector = () => {
  const { editingNodeId, nodes } = useWorkflowEditorStore()
  const node = nodes.find(n => n.id === editingNodeId)
  const entry = node ? getNodeEntry(node.data.nodeType) : null

  return (
    <Sheet open={!!node} onOpenChange={open => !open && editNode(null)}>
      <SheetContent>
        {entry && node && (
          <>
            <NodeInspectorHeader definition={entry.definition} data={node.data} />
            <entry.panel id={node.id} data={node.data} />
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
```

### 4.4 Extensibility Checklist

Adding a new node type (e.g. "HTTP Request"):

| Step | File | What to do |
|------|------|-----------|
| 1 | `nodes/http/index.ts` | Export `definition`, `NodeComponent`, `PanelComponent` |
| 2 | `nodes/http/node.tsx` | Canvas body content |
| 3 | `nodes/http/panel.tsx` | Config panel |
| 4 | `nodes/registry.ts` | Add 1 import + 1 line to `REGISTRY` array |

**Zero changes to:** BaseNode, Canvas, NodeInspector, NodePalette, store, types.

Things that work automatically:
- NodePalette reads `getAllDefinitions()` — new node appears
- BaseNode renders icon/color/handles from definition
- NodeInspector routes to the new panel
- Save/load works (config stored as JSONB)
- Categories/search work via `definition.category`/`definition.label`

### 4.5 Handle Interactions

| Action | Result |
|--------|--------|
| Click "+" on output handle | Opens NodePalette with context → auto-connects new node |
| Drag from output handle | Creates edge to target node |
| Click "+" top-right button | Opens NodePalette without context → place at center |
| Single click node | Select (highlight border) |
| Double click node | Open NodeInspector sheet |
| Click canvas | Deselect + close inspector |
| Delete/Backspace on selected | Remove node + connected edges |

### 4.6 Auto Start Node

When loading an empty workflow:
- Auto-create Start node at `{ x: 250, y: 250 }`
- Start + End nodes: `canDelete: false` in definition (BaseNode hides delete button)

---

## 5. Migration Path from Current Code

### Phase 1: Node Registry + Types
- Create `nodes/types.ts` with `HandlePort`, `NodeTypeDefinition`, `NodeRegistryEntry`
- Create `nodes/registry.ts` with explicit map
- Create per-node `index.ts` files exporting definition + components
- Temporarily keep existing BaseNode working during migration

### Phase 2: BaseNode + Composition
- Refactor BaseNode to use registry lookup (no more `NODE_TYPE_MAP`)
- Remove centralized `ICON_MAP` (icons come from definition)
- Create per-node `node.tsx` (most nodes just return `null` for default look)

### Phase 3: Per-Node Panels
- Create per-node `panel.tsx` replacing generic `ConfigFieldInput`
- NodeInspector routes via `entry.panel`
- Keep shared field components in `components/node-inspector/fields/`

### Phase 4: Handle System
- Replace numeric `handles.inputs/outputs` with `HandlePort[]` arrays
- Create `SourceHandle`/`TargetHandle` with "+" button
- Add `addNodeContext` to store
- Implement dynamic handles for condition node

### Phase 5: Polish
- Auto Start node on empty workflow
- Custom edge rendering with status colors
- Keyboard shortcuts
- Node palette categories + improved search
