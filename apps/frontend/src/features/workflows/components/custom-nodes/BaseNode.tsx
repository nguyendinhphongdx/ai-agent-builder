"use client";

import type { ReactNode } from "react";
import { Check, Loader2, X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { NodeTypeDefinition } from "../../nodes/types";
import type { NodeRunStatus } from "../../stores/workflowEditorStore";
import { SourceHandle, TargetHandle, SubHandle } from "../handles";

interface BaseNodeProps {
  nodeId: string;
  definition: NodeTypeDefinition;
  label?: string;
  selected?: boolean;
  customHandles?: boolean;
  runStatus?: NodeRunStatus;
  children?: ReactNode;
}

/**
 * n8n-style node shapes:
 * - start/webhook_trigger: rounded-l-full (pill left)
 * - end: rounded-r-full (pill right)
 * - default: rounded-xl
 */
function getNodeShape(type: string): string {
  switch (type) {
    case "start":
    case "webhook_trigger":
      return "rounded-l-full rounded-r-xl";
    case "end":
      return "rounded-r-full rounded-l-xl";
    default:
      return "rounded-xl";
  }
}

export function BaseNode({
  nodeId,
  definition,
  label,
  selected,
  customHandles,
  runStatus,
  children,
}: BaseNodeProps) {
  const Icon = definition.icon;
  const shape = getNodeShape(definition.type);
  const hasSubs = definition.subConnections && definition.subConnections.length > 0;

  return (
    <div className="relative flex flex-col items-center">
      {/* Main row: input → body → output */}
      <div className="relative flex items-center">
        {/* Input handles */}
        {definition.handles.inputs.map((port) => (
          <TargetHandle key={port.id} handleId={port.id} label={port.label} />
        ))}

        {/* Node body */}
        <div
          className={cn(
            "flex items-center gap-2.5 border bg-card px-4 py-3 shadow-sm min-w-35",
            shape,
            selected
              ? "border-primary ring-2 ring-primary/20"
              : runStatus === "failed"
                ? "border-destructive ring-2 ring-destructive/20"
                : runStatus === "completed"
                  ? "border-emerald-500 ring-2 ring-emerald-500/20"
                  : "border-border",
          )}
        >
          {/* Run status indicator */}
          {runStatus && (
            <div className="absolute -top-2 -right-2 z-10">
              {runStatus === "running" && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" />
                </div>
              )}
              {runStatus === "completed" && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white">
                  <Check className="h-3 w-3" />
                </div>
              )}
              {runStatus === "failed" && (
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground">
                  <X className="h-3 w-3" />
                </div>
              )}
            </div>
          )}
          <div
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${definition.color}20` }}
          >
            <Icon className="h-4 w-4" style={{ color: definition.color }} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-medium leading-tight truncate max-w-30">
              {label || definition.label}
            </p>
            <p className="text-[10px] text-muted-foreground leading-tight">
              {definition.type}
            </p>
          </div>
        </div>

        {/* Per-node content (condition branches etc.) */}
        {children && (
          <div className="absolute top-full left-0 right-0 mt-1">{children}</div>
        )}

        {/* Output handles */}
        {!customHandles &&
          definition.handles.outputs.map((port) => (
            <SourceHandle
              key={port.id}
              handleId={port.id}
              nodeId={nodeId}
              label={port.label}
            />
          ))}
      </div>

      {/* Sub-connections at bottom (model, memory, tools) */}
      {hasSubs && (
        <div className="flex items-start gap-4 mt-1">
          {definition.subConnections!.map((sub) => (
            <SubHandle
              key={sub.id}
              handleId={`sub_${sub.id}`}
              nodeId={nodeId}
              label={sub.label}
              required={sub.required}
            />
          ))}
        </div>
      )}
    </div>
  );
}
