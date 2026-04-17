"use client";

import { useTheme } from "next-themes";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { ExecutionNode } from "./custom-nodes/ExecutionNode";
import { getNodeEntry } from "../nodes/registry";

const nodeTypes: NodeTypes = {
  baseNode: ExecutionNode,
};

interface NodeExecution {
  node_id: string;
  node_type: string;
  label: string | null;
  status: string;
  input_data: unknown;
  output_data: unknown;
  error: string | null;
  tokens_used: number;
  started_at: string | null;
  completed_at: string | null;
}

interface ExecutionCanvasProps {
  nodes: Node[];
  edges: Edge[];
  executionMap: Map<string, NodeExecution>;
}

export function ExecutionCanvas({ nodes, edges, executionMap }: ExecutionCanvasProps) {
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  // Color edges based on execution status
  const styledEdges = edges.map((edge) => {
    const sourceExec = executionMap.get(edge.source);
    const targetExec = executionMap.get(edge.target);

    let strokeColor = isDark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)";
    let animated = false;

    if (sourceExec?.status === "completed" && targetExec?.status === "completed") {
      strokeColor = "#10b981"; // emerald
    } else if (sourceExec?.status === "completed" && targetExec) {
      strokeColor = "#10b981";
      animated = true;
    } else if (sourceExec?.status === "failed" || sourceExec?.status === "error") {
      strokeColor = "#ef4444"; // red
    }

    return {
      ...edge,
      animated,
      style: {
        stroke: strokeColor,
        strokeWidth: 2,
      },
    };
  });

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={styledEdges}
        nodeTypes={nodeTypes}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag
        zoomOnScroll
        fitView
        proOptions={{ hideAttribution: true }}
        className="bg-background"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color={isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)"}
        />
        <Controls
          showInteractive={false}
          className="rounded-xl! border! border-border! bg-card! shadow-md! [&>button]:border-border! [&>button]:bg-card! [&>button]:text-foreground! [&>button]:hover:bg-accent!"
        />
        <MiniMap
          nodeColor={(node) => {
            const exec = executionMap.get(node.id);
            if (exec?.status === "completed") return "#10b981";
            if (exec?.status === "failed" || exec?.status === "error") return "#ef4444";
            const entry = getNodeEntry(node.data?.nodeType as string);
            return entry?.definition.color ?? (isDark ? "#444" : "#ccc");
          }}
          nodeStrokeWidth={0}
          nodeBorderRadius={6}
          maskColor={isDark ? "rgba(0,0,0,0.75)" : "rgba(255,255,255,0.75)"}
          maskStrokeColor="transparent"
          pannable
          zoomable
          className="rounded-xl! border! border-border! bg-card/80! shadow-md!"
          style={{ width: 160, height: 100 }}
        />
      </ReactFlow>
    </div>
  );
}
