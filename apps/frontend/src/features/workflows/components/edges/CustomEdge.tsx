"use client";

import { useState } from "react";
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  type EdgeProps,
} from "@xyflow/react";
import { Plus, Trash2 } from "lucide-react";
import { useWorkflowEditorStore } from "../../stores/workflowEditorStore";

export function CustomEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  source,
  sourceHandleId,
  selected,
}: EdgeProps) {
  const [hovered, setHovered] = useState(false);
  const { onEdgesChange, openNodePalette } = useWorkflowEditorStore();

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    curvature: 0.3,
  });

  const active = hovered || selected;
  const strokeColor = active
    ? "var(--primary)"
    : "color-mix(in oklch, var(--muted-foreground) 55%, transparent)";

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdgesChange([{ id, type: "remove" }]);
  };

  const handleAdd = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (source && sourceHandleId) {
      openNodePalette({ sourceNodeId: source, sourceHandleId });
    }
  };

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        interactionWidth={24}
        style={{
          stroke: strokeColor,
          strokeWidth: active ? 2.5 : 2,
          strokeLinecap: "round",
          transition: "stroke 0.15s, stroke-width 0.15s",
        }}
      />

      {/* Invisible hover area */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={24}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />

      <EdgeLabelRenderer>
        <div
          className="nodrag nopan absolute flex items-center gap-1"
          style={{
            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
            pointerEvents: "all",
            opacity: hovered ? 1 : 0,
            transition: "opacity 0.15s",
          }}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <button
            onClick={handleAdd}
            className="flex h-6 w-6 items-center justify-center rounded-md border border-border bg-background text-muted-foreground shadow-sm transition-colors hover:bg-accent hover:text-foreground hover:border-primary"
          >
            <Plus className="h-3 w-3" />
          </button>
          <button
            onClick={handleDelete}
            className="flex h-6 w-6 items-center justify-center rounded-md border border-border bg-background text-muted-foreground shadow-sm transition-colors hover:bg-destructive hover:text-destructive-foreground hover:border-destructive"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
}
