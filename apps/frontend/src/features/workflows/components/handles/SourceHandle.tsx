"use client";

import { Handle, Position, useEdges } from "@xyflow/react";
import { useWorkflowEditorStore } from "../../stores/workflowEditorStore";
import { HandlePlus } from "./HandlePlus";

interface SourceHandleProps {
  handleId: string;
  nodeId: string;
  label?: string;
}

export function SourceHandle({ handleId, nodeId, label }: SourceHandleProps) {
  const edges = useEdges();
  const openNodePalette = useWorkflowEditorStore((s) => s.openNodePalette);

  const isConnected = edges.some(
    (e) =>
      e.source === nodeId &&
      (e.sourceHandle === handleId ||
        (!e.sourceHandle && handleId === "default"))
  );

  return (
    <>
      <Handle
        type="source"
        position={Position.Right}
        id={handleId}
        className="w-2.5! h-2.5! bg-muted-foreground/40! border-2! border-background!"
      />
      {label && (
        <span className="absolute right-5 top-1/2 -translate-y-1/2 text-[9px] font-medium text-muted-foreground whitespace-nowrap">
          {label}
        </span>
      )}
      {!isConnected && (
        <HandlePlus
          onClick={() =>
            openNodePalette({ sourceNodeId: nodeId, sourceHandleId: handleId })
          }
        />
      )}
    </>
  );
}
