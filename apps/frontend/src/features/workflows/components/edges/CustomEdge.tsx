"use client";

import { useState } from "react";
import {
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
  style,
  source,
  sourceHandleId,
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
  });

  const arrowId = `arrow-${id}`;
  const strokeColor = hovered
    ? "hsl(var(--primary))"
    : "hsl(var(--muted-foreground) / 0.4)";

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
      {/* Arrow marker definition */}
      <defs>
        <marker
          id={arrowId}
          viewBox="0 0 10 10"
          refX="10"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto"
        >
          <path d="M 0 1 L 10 5 L 0 9 z" fill={strokeColor} />
        </marker>
      </defs>

      {/* Invisible wider hit area */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={20}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />

      {/* Visible edge — arrow only at target end */}
      <path
        d={edgePath}
        fill="none"
        stroke={strokeColor}
        strokeWidth={hovered ? 2 : 1.5}
        markerEnd={`url(#${arrowId})`}
        style={style}
      />

      {/* Hover toolbar */}
      {hovered && (
        <EdgeLabelRenderer>
          <div
            className="nodrag nopan pointer-events-auto absolute flex items-center gap-1"
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
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
      )}
    </>
  );
}
