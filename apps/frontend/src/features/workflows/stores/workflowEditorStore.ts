import { create } from "zustand";
import {
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type OnConnect,
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
} from "@xyflow/react";
import { getNodeEntry } from "../nodes/registry";
import type { NodeRunStatus } from "../types";

export type { NodeRunStatus };

export interface AddNodeContext {
  sourceNodeId: string;
  sourceHandleId: string;
  /** When true, the referenced handle is a TARGET (e.g. sub-connections like
   * an agent's "model" slot). The new node should connect UP into it as the
   * source, not OUT from it as the target. */
  isSubConnection?: boolean;
}

interface HistorySnapshot {
  nodes: Node[];
  edges: Edge[];
}

const MAX_HISTORY = 50;

// Module-scoped clipboard — copy/paste within the same tab session. Lives
// outside the store so it doesn't trigger React re-renders on every copy.
let clipboard: { nodes: Node[]; edges: Edge[] } | null = null;

interface WorkflowEditorState {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  editingNodeId: string | null;
  isDirty: boolean;
  nodePaletteOpen: boolean;
  addNodeContext: AddNodeContext | null;
  nodeStatuses: Record<string, NodeRunStatus>;

  // History — internal undo/redo stacks. Mutations push the *previous* state
  // onto `past`; undo() pops it and shelves the current state onto `future`.
  past: HistorySnapshot[];
  future: HistorySnapshot[];
  _dragHistoryPushed: boolean;

  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  addNode: (node: Node) => void;
  removeNode: (id: string) => void;
  duplicateNode: (id: string) => void;
  updateNodeData: (id: string, data: Record<string, unknown>) => void;
  selectNode: (id: string | null) => void;
  editNode: (id: string | null) => void;
  openNodePalette: (context?: AddNodeContext) => void;
  closeNodePalette: () => void;
  setNodeStatus: (nodeId: string, status: NodeRunStatus) => void;
  clearNodeStatuses: () => void;
  setDirty: (dirty: boolean) => void;
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
  selectAll: () => void;
  copySelection: () => void;
  pasteFromClipboard: () => void;
  reset: () => void;
}

export const useWorkflowEditorStore = create<WorkflowEditorState>(
  (set, get) => {
    /** Snapshot the *current* graph and push onto `past`, clearing `future`. */
    const pushHistory = () => {
      const { nodes, edges, past } = get();
      const next = [...past, { nodes, edges }];
      if (next.length > MAX_HISTORY) next.shift();
      set({ past: next, future: [] });
    };

    return {
      nodes: [],
      edges: [],
      selectedNodeId: null,
      editingNodeId: null,
      isDirty: false,
      nodePaletteOpen: false,
      addNodeContext: null,
      nodeStatuses: {},
      past: [],
      future: [],
      _dragHistoryPushed: false,

      // Hydration paths — replace state without polluting history.
      setNodes: (nodes) => set({ nodes, past: [], future: [] }),
      setEdges: (edges) => set({ edges, past: [], future: [] }),

      onNodesChange: (changes) => {
        // Push history exactly once per drag (at the start) so undo restores
        // the pre-drag positions; skip pure select/dimension churn.
        const positionChanges = changes.filter((c) => c.type === "position");
        const dragStart = positionChanges.some((c) => c.dragging === true);
        const dragEnd = positionChanges.some((c) => c.dragging === false);
        const hasStructuralChange = changes.some(
          (c) => c.type === "remove" || c.type === "add" || c.type === "replace",
        );

        if (hasStructuralChange) {
          pushHistory();
        } else if (dragStart && !get()._dragHistoryPushed) {
          pushHistory();
          set({ _dragHistoryPushed: true });
        }

        const isMutating = hasStructuralChange || positionChanges.length > 0;

        set({
          nodes: applyNodeChanges(changes, get().nodes),
          isDirty: isMutating ? true : get().isDirty,
          ...(dragEnd ? { _dragHistoryPushed: false } : {}),
        });
      },

      onEdgesChange: (changes) => {
        const hasStructuralChange = changes.some(
          (c) => c.type === "remove" || c.type === "add" || c.type === "replace",
        );
        if (hasStructuralChange) pushHistory();

        set({
          edges: applyEdgeChanges(changes, get().edges),
          isDirty: hasStructuralChange ? true : get().isDirty,
        });
      },

      onConnect: (connection) => {
        pushHistory();
        const newEdge: Edge = {
          ...connection,
          id: crypto.randomUUID(),
          type: "customEdge",
        };
        set({
          edges: addEdge(newEdge, get().edges),
          isDirty: true,
        });
      },

      addNode: (node) => {
        const entry = getNodeEntry((node.data as { nodeType?: string }).nodeType ?? "");
        const isEntry =
          entry?.definition.type === "start" ||
          entry?.definition.category === "trigger";

        let nodes = get().nodes;
        let edges = get().edges;

        // A workflow has exactly one entry. Adding another one evicts the old.
        if (isEntry) {
          const existingEntries = nodes.filter((n) => {
            const e = getNodeEntry((n.data as { nodeType?: string }).nodeType ?? "");
            return e?.definition.type === "start" || e?.definition.category === "trigger";
          });
          if (existingEntries.length > 0) {
            const evictIds = new Set(existingEntries.map((n) => n.id));
            nodes = nodes.filter((n) => !evictIds.has(n.id));
            edges = edges.filter(
              (e) => !evictIds.has(e.source) && !evictIds.has(e.target),
            );
          }
        }

        pushHistory();
        set({ nodes: [...nodes, node], edges, isDirty: true });
      },

      removeNode: (id) => {
        const node = get().nodes.find((n) => n.id === id);
        if (node) {
          const entry = getNodeEntry(node.data.nodeType as string);
          if (entry?.definition.canDelete === false) return;
        }
        pushHistory();
        set({
          nodes: get().nodes.filter((n) => n.id !== id),
          edges: get().edges.filter(
            (e) => e.source !== id && e.target !== id,
          ),
          selectedNodeId:
            get().selectedNodeId === id ? null : get().selectedNodeId,
          editingNodeId:
            get().editingNodeId === id ? null : get().editingNodeId,
          isDirty: true,
        });
      },

      duplicateNode: (id) => {
        const source = get().nodes.find((n) => n.id === id);
        if (!source) return;

        // Trigger/start nodes are singleton — duplicating would just evict the
        // original via addNode's eviction rule, which is surprising UX. Skip.
        const entry = getNodeEntry((source.data as { nodeType?: string }).nodeType ?? "");
        if (
          entry?.definition.type === "start" ||
          entry?.definition.category === "trigger"
        ) {
          return;
        }

        const clone: Node = {
          ...source,
          id: crypto.randomUUID(),
          position: { x: source.position.x + 40, y: source.position.y + 40 },
          selected: false,
          data: { ...source.data, config: { ...(source.data.config as object) } },
        };

        pushHistory();
        set({
          nodes: [...get().nodes, clone],
          selectedNodeId: clone.id,
          isDirty: true,
        });
      },

      updateNodeData: (id, data) => {
        pushHistory();
        set({
          nodes: get().nodes.map((n) =>
            n.id === id ? { ...n, data: { ...n.data, ...data } } : n,
          ),
          isDirty: true,
        });
      },

      selectNode: (id) => set({ selectedNodeId: id }),

      editNode: (id) => set({ editingNodeId: id }),

      openNodePalette: (context) =>
        set({ nodePaletteOpen: true, addNodeContext: context ?? null }),

      closeNodePalette: () =>
        set({ nodePaletteOpen: false, addNodeContext: null }),

      setNodeStatus: (nodeId, status) =>
        set({ nodeStatuses: { ...get().nodeStatuses, [nodeId]: status } }),

      clearNodeStatuses: () => set({ nodeStatuses: {} }),

      setDirty: (dirty) => set({ isDirty: dirty }),

      undo: () => {
        const { past, future, nodes, edges } = get();
        if (past.length === 0) return;
        const previous = past[past.length - 1];
        set({
          past: past.slice(0, -1),
          future: [...future, { nodes, edges }],
          nodes: previous.nodes,
          edges: previous.edges,
          isDirty: true,
        });
      },

      redo: () => {
        const { past, future, nodes, edges } = get();
        if (future.length === 0) return;
        const next = future[future.length - 1];
        set({
          past: [...past, { nodes, edges }],
          future: future.slice(0, -1),
          nodes: next.nodes,
          edges: next.edges,
          isDirty: true,
        });
      },

      canUndo: () => get().past.length > 0,
      canRedo: () => get().future.length > 0,

      selectAll: () => {
        set({
          nodes: get().nodes.map((n) => ({ ...n, selected: true })),
          edges: get().edges.map((e) => ({ ...e, selected: true })),
        });
      },

      copySelection: () => {
        const { nodes, edges } = get();
        const selectedNodes = nodes.filter((n) => n.selected);
        if (selectedNodes.length === 0) return;
        const selectedIds = new Set(selectedNodes.map((n) => n.id));
        // Only copy edges whose both endpoints are part of the selection — a
        // dangling edge wouldn't reconnect to anything when pasted.
        const internalEdges = edges.filter(
          (e) => selectedIds.has(e.source) && selectedIds.has(e.target),
        );
        clipboard = {
          nodes: selectedNodes.map((n) => structuredClone(n)),
          edges: internalEdges.map((e) => structuredClone(e)),
        };
      },

      pasteFromClipboard: () => {
        if (!clipboard || clipboard.nodes.length === 0) return;

        const idMap = new Map<string, string>();
        const newNodes: Node[] = [];
        for (const src of clipboard.nodes) {
          // Trigger/start nodes are singleton — pasting them would silently
          // evict the existing entry through addNode's rule. Skip them.
          const entry = getNodeEntry((src.data as { nodeType?: string }).nodeType ?? "");
          const isEntry =
            entry?.definition.type === "start" ||
            entry?.definition.category === "trigger";
          if (isEntry) continue;

          const newId = crypto.randomUUID();
          idMap.set(src.id, newId);
          newNodes.push({
            ...src,
            id: newId,
            position: { x: src.position.x + 40, y: src.position.y + 40 },
            selected: true,
          });
        }
        if (newNodes.length === 0) return;

        const newEdges: Edge[] = [];
        for (const src of clipboard.edges) {
          const newSource = idMap.get(src.source);
          const newTarget = idMap.get(src.target);
          if (!newSource || !newTarget) continue;
          newEdges.push({
            ...src,
            id: crypto.randomUUID(),
            source: newSource,
            target: newTarget,
            selected: false,
          });
        }

        pushHistory();
        // Deselect existing items so the freshly pasted cluster is the active
        // selection — matches Figma/n8n behaviour.
        set({
          nodes: [
            ...get().nodes.map((n) => ({ ...n, selected: false })),
            ...newNodes,
          ],
          edges: [
            ...get().edges.map((e) => ({ ...e, selected: false })),
            ...newEdges,
          ],
          isDirty: true,
        });
      },

      reset: () =>
        set({
          nodes: [],
          edges: [],
          selectedNodeId: null,
          editingNodeId: null,
          isDirty: false,
          nodePaletteOpen: false,
          addNodeContext: null,
          nodeStatuses: {},
          past: [],
          future: [],
          _dragHistoryPushed: false,
        }),
    };
  },
);
