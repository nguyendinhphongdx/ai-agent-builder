"use client";

import { Handle, Position, useEdges } from "@xyflow/react";
import { Plus } from "lucide-react";
import { useWorkflowEditorStore } from "../../stores/workflowEditorStore";

interface SubHandleProps {
  handleId: string;
  nodeId: string;
  label: string;
  required?: boolean;
}

export function SubHandle({ handleId, nodeId, label, required }: SubHandleProps) {
  const edges = useEdges();
  const openNodePalette = useWorkflowEditorStore((s) => s.openNodePalette);

  const isConnected = edges.some(
    (e) => e.target === nodeId && e.targetHandle === handleId
  );

  return (
    <div className="group relative flex flex-col items-center gap-1.5">
      {/* Diamond slot — Handle overlays this box so the connection point
          lines up visually with the drawn diamond. */}
      <div className="relative flex h-4 w-4 items-center justify-center">
        <div className="h-3 w-3 rotate-45 border-2 border-background bg-muted-foreground/40 transition-colors group-hover:bg-primary" />
        <Handle
          type="target"
          position={Position.Top}
          id={handleId}
          className="absolute! top-1/2! left-1/2! h-4! w-4! -translate-x-1/2! -translate-y-1/2! transform! rounded-none! border-0! bg-transparent! opacity-0!"
        />
      </div>

      {/* Label */}
      <span className="text-[10px] leading-none text-muted-foreground whitespace-nowrap">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </span>

      {/* Plus button — shows on hover when not connected */}
      {!isConnected && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            openNodePalette({
              sourceNodeId: nodeId,
              sourceHandleId: handleId,
              isSubConnection: true,
            });
          }}
          className="flex h-5 w-5 items-center justify-center rounded-md border border-dashed border-border bg-background text-muted-foreground opacity-0 shadow-sm transition-all hover:border-primary hover:bg-accent hover:text-foreground group-hover:opacity-100"
        >
          <Plus className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}
