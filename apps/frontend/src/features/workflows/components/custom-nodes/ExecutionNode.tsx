"use client";

import { memo, createElement } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { getNodeEntry } from "../../nodes/registry";
import type { NodeData } from "../../nodes/types";

/**
 * Read-only node for execution view.
 * Shows execution status overlay (green/red border, check/x icon).
 */
function ExecutionNodeComponent({ id, data, selected }: NodeProps) {
  const nodeData = data as unknown as NodeData & {
    _executionStatus?: string;
    _executionError?: string | null;
  };

  const entry = getNodeEntry(nodeData.nodeType);
  if (!entry) return null;

  const def = entry.definition;
  const Icon = def.icon;
  const execStatus = nodeData._executionStatus;

  const hasExecution = !!execStatus;
  const isSuccess = execStatus === "completed";
  const isFailed = execStatus === "failed" || execStatus === "error";

  return (
    <>
      {/* Input handles */}
      {def.handles.inputs.map((port) => (
        <Handle
          key={port.id}
          type="target"
          position={Position.Left}
          id={port.id}
          className="w-2.5! h-2.5! bg-muted-foreground/40! border-2! border-background!"
        />
      ))}

      <div
        className={cn(
          "relative min-w-40 rounded-xl border-2 bg-card px-3 py-2.5 shadow-sm transition-all",
          hasExecution && isSuccess && "border-emerald-500 shadow-emerald-500/10",
          hasExecution && isFailed && "border-red-500 shadow-red-500/10",
          !hasExecution && "border-border opacity-50",
        )}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${def.color}20` }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color: def.color }} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate">
              {nodeData.label || def.label}
            </p>
            <p className="text-[10px] text-muted-foreground">{def.type}</p>
          </div>

          {/* Execution status icon */}
          {hasExecution && (
            <div className="shrink-0">
              {isSuccess ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              ) : isFailed ? (
                <XCircle className="h-4 w-4 text-red-500" />
              ) : null}
            </div>
          )}
        </div>

        {/* Per-node content */}
        {createElement(entry.node, { id, data: nodeData })}
      </div>

      {/* Output handles */}
      {def.handles.outputs.map((port) => (
        <Handle
          key={port.id}
          type="source"
          position={Position.Right}
          id={port.id}
          className="w-2.5! h-2.5! bg-muted-foreground/40! border-2! border-background!"
        />
      ))}
    </>
  );
}

export const ExecutionNode = memo(ExecutionNodeComponent);
