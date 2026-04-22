"use client";

import { useCallback } from "react";
import { useReactFlow, type Node, type Edge } from "@xyflow/react";
import ELK, { type ElkNode } from "elkjs/lib/elk.bundled.js";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";
import { getNodeEntry } from "../nodes/registry";
import { NodeConnectionTypes } from "../nodes/types";

const elk = new ELK();

const ELK_OPTIONS = {
  "elk.algorithm": "layered",
  "elk.direction": "RIGHT",
  "elk.layered.spacing.nodeNodeBetweenLayers": "80",
  "elk.spacing.nodeNode": "50",
  "elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX",
};

/**
 * Returns true if either endpoint of the edge is a non-main (ai_*) port.
 * Those edges are sub-connections (Chat Model / Memory / Tool slots) and should
 * not participate in the main-flow layered layout.
 */
function isSubConnectionEdge(edge: Edge, nodes: Node[]): boolean {
  const src = nodes.find((n) => n.id === edge.source);
  const tgt = nodes.find((n) => n.id === edge.target);

  const srcType = src && getNodeEntry((src.data as { nodeType?: string }).nodeType ?? "")
    ?.definition.handles.outputs.find((p) => p.id === edge.sourceHandle)?.type;
  const tgtType = tgt && getNodeEntry((tgt.data as { nodeType?: string }).nodeType ?? "")
    ?.definition.handles.inputs.find((p) => p.id === edge.targetHandle)?.type;

  return (
    (srcType !== undefined && srcType !== NodeConnectionTypes.Main) ||
    (tgtType !== undefined && tgtType !== NodeConnectionTypes.Main)
  );
}

/**
 * Hook that returns an `autoLayout` function.
 * Uses ELK.js to compute a clean left-to-right layered layout,
 * then updates node positions and fits the view.
 */
export function useAutoLayout() {
  const { nodes, edges, setNodes } = useWorkflowEditorStore();
  const { fitView } = useReactFlow();

  return useCallback(async () => {
    if (nodes.length === 0) return;

    const graph: ElkNode = {
      id: "root",
      layoutOptions: ELK_OPTIONS,
      children: nodes.map((node) => ({
        id: node.id,
        width: node.measured?.width ?? 180,
        height: node.measured?.height ?? 60,
      })),
      edges: edges
        .filter((e) => !isSubConnectionEdge(e, nodes))
        .map((edge) => ({
          id: edge.id,
          sources: [edge.source],
          targets: [edge.target],
        })),
    };

    try {
      const result = await elk.layout(graph);
      const layouted = nodes.map((node) => {
        const laidOut = result.children?.find((n) => n.id === node.id);
        if (!laidOut) return node;
        return {
          ...node,
          position: { x: laidOut.x ?? 0, y: laidOut.y ?? 0 },
        };
      });

      setNodes(layouted);
      setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 50);
    } catch (err) {
      console.error("Auto-layout failed:", err);
    }
  }, [nodes, edges, setNodes, fitView]);
}
