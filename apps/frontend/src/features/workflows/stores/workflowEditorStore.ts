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

export interface AddNodeContext {
  sourceNodeId: string;
  sourceHandleId: string;
  /** When true, the referenced handle is a TARGET (e.g. sub-connections like
   * an agent's "model" slot). The new node should connect UP into it as the
   * source, not OUT from it as the target. */
  isSubConnection?: boolean;
}

export type NodeRunStatus = "running" | "completed" | "failed";

interface WorkflowEditorState {
  nodes: Node[];
  edges: Edge[];
  selectedNodeId: string | null;
  editingNodeId: string | null;
  isDirty: boolean;
  nodePaletteOpen: boolean;
  addNodeContext: AddNodeContext | null;
  nodeStatuses: Record<string, NodeRunStatus>;

  setNodes: (nodes: Node[]) => void;
  setEdges: (edges: Edge[]) => void;
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  addNode: (node: Node) => void;
  removeNode: (id: string) => void;
  updateNodeData: (id: string, data: Record<string, unknown>) => void;
  selectNode: (id: string | null) => void;
  editNode: (id: string | null) => void;
  openNodePalette: (context?: AddNodeContext) => void;
  closeNodePalette: () => void;
  setNodeStatus: (nodeId: string, status: NodeRunStatus) => void;
  clearNodeStatuses: () => void;
  setDirty: (dirty: boolean) => void;
  reset: () => void;
}

export const useWorkflowEditorStore = create<WorkflowEditorState>(
  (set, get) => ({
    nodes: [],
    edges: [],
    selectedNodeId: null,
    editingNodeId: null,
    isDirty: false,
    nodePaletteOpen: false,
    addNodeContext: null,
    nodeStatuses: {},

    setNodes: (nodes) => set({ nodes }),
    setEdges: (edges) => set({ edges }),

    onNodesChange: (changes) => {
      set({
        nodes: applyNodeChanges(changes, get().nodes),
        isDirty: true,
      });
    },

    onEdgesChange: (changes) => {
      set({
        edges: applyEdgeChanges(changes, get().edges),
        isDirty: true,
      });
    },

    onConnect: (connection) => {
      const newEdge = {
        ...connection,
        id: crypto.randomUUID(),
        type: "customEdge",
      };
      set({
        edges: addEdge(newEdge, get().edges as any),
        isDirty: true,
      });
    },

    addNode: (node) => {
      set({ nodes: [...get().nodes, node], isDirty: true });
    },

    removeNode: (id) => {
      const node = get().nodes.find((n) => n.id === id);
      if (node) {
        const entry = getNodeEntry(node.data.nodeType as string);
        if (entry?.definition.canDelete === false) return;
      }
      set({
        nodes: get().nodes.filter((n) => n.id !== id),
        edges: get().edges.filter(
          (e) => e.source !== id && e.target !== id
        ),
        selectedNodeId:
          get().selectedNodeId === id ? null : get().selectedNodeId,
        editingNodeId:
          get().editingNodeId === id ? null : get().editingNodeId,
        isDirty: true,
      });
    },

    updateNodeData: (id, data) => {
      set({
        nodes: get().nodes.map((n) =>
          n.id === id ? { ...n, data: { ...n.data, ...data } } : n
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

    reset: () =>
      set({ nodes: [], edges: [], selectedNodeId: null, editingNodeId: null, isDirty: false, nodePaletteOpen: false, addNodeContext: null, nodeStatuses: {} }),
  })
);
