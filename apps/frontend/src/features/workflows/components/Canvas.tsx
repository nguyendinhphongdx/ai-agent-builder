"use client";

import { useCallback, useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  type NodeTypes,

  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { CustomNode } from "./custom-nodes/CustomNode";
import { getNodeEntry } from "../nodes/registry";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";

const nodeTypes: NodeTypes = {
  baseNode: CustomNode,
};

export function Canvas() {
  const {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    selectNode,
    editNode,
    removeNode,
    selectedNodeId,
    closeNodePalette,
  } = useWorkflowEditorStore();

  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const reactFlowRef = useRef<ReactFlowInstance | null>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const nodeType = e.dataTransfer.getData("nodeType");
      if (!nodeType || !reactFlowRef.current) return;

      const position = reactFlowRef.current.screenToFlowPosition({
        x: e.clientX,
        y: e.clientY,
      });

      const entry = getNodeEntry(nodeType);
      const defaultData = entry?.definition.defaultData?.() ?? {};

      addNode({
        id: crypto.randomUUID(),
        type: "baseNode",
        position,
        data: { nodeType, label: "", config: defaultData },
      });
    },
    [addNode]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "Escape") {
        selectNode(null);
        editNode(null);
        closeNodePalette();
      }
      if ((e.key === "Delete" || e.key === "Backspace") && selectedNodeId) {
        removeNode(selectedNodeId);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selectedNodeId, selectNode, editNode, removeNode, closeNodePalette]);

  return (
    <div className="h-full w-full" onDrop={handleDrop} onDragOver={handleDragOver}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={(instance) => {
          reactFlowRef.current = instance;
        }}
        onPaneClick={() => { selectNode(null); editNode(null); }}
        onNodeClick={(_event, node) => selectNode(node.id)}
        onNodeDoubleClick={(_event, node) => { selectNode(node.id); editNode(node.id); }}
        nodeTypes={nodeTypes}
        deleteKeyCode={null}
        fitView
        fitViewOptions={{ maxZoom: 0.85, padding: 0.3 }}
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        className="bg-background"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1.5}
          color={isDark ? "rgba(255,255,255,0.15)" : "rgba(0,0,0,0.15)"}
        />
        <Controls
          showInteractive={false}
          className="rounded-lg! border! border-border! bg-background! shadow-sm! [&>button]:border-border! [&>button]:bg-background! [&>button]:text-foreground! [&>button]:hover:bg-accent!"
        />
        <MiniMap
          nodeColor={(node) => {
            const entry = getNodeEntry(node.data?.nodeType as string);
            return entry?.definition.color ?? (isDark ? "#444" : "#ccc");
          }}
          nodeStrokeWidth={2}
          maskColor={isDark ? "rgba(0,0,0,0.7)" : "rgba(0,0,0,0.06)"}
          maskStrokeColor={isDark ? "rgba(255,255,255,0.2)" : "rgba(0,0,0,0.15)"}
          maskStrokeWidth={1}
          pannable
          zoomable
          className="rounded-xl! border! border-border! bg-muted/50! shadow-sm!"
          style={{ width: 160, height: 100 }}
        />
      </ReactFlow>
    </div>
  );
}
