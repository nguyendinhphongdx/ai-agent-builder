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
    <div className="relative flex flex-col items-center gap-1">
      {/* Diamond handle */}
      <Handle
        type="target"
        position={Position.Bottom}
        id={handleId}
        className="w-3! h-3! rounded-none! rotate-45! bg-muted-foreground/40! border-2! border-background!"
      />

      {/* Label */}
      <span className="text-[9px] text-muted-foreground whitespace-nowrap mt-2">
        {label}
        {required && <span className="text-destructive">*</span>}
      </span>

      {/* Plus button when not connected */}
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
          className="flex h-4 w-4 items-center justify-center rounded border border-border bg-background text-muted-foreground shadow-sm transition-colors hover:bg-accent hover:text-foreground hover:border-primary"
        >
          <Plus className="h-2.5 w-2.5" />
        </button>
      )}
    </div>
  );
}
