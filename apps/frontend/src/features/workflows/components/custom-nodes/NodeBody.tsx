"use client";

import type { ComponentType } from "react";
import { Check, Loader2, Pin, X } from "lucide-react";
import type { NodeRunStatus } from "../../stores/workflowEditorStore";

interface NodeBodyProps {
  icon: ComponentType<{ className?: string; style?: React.CSSProperties }>;
  color: string;
  label: string;
  sublabel: string;
  runStatus?: NodeRunStatus;
  isPinned?: boolean;
}

/**
 * Visual content of a node: icon, label, run status badge.
 */
export function NodeBody({
  icon: Icon,
  color,
  label,
  sublabel,
  runStatus,
  isPinned,
}: NodeBodyProps) {
  return (
    <>
      {/* Pin indicator — output frozen, executor will be skipped on full runs */}
      {isPinned && (
        <div
          className="absolute -top-2 -left-2 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-white shadow-sm"
          title="Output pinned"
        >
          <Pin className="h-3 w-3" />
        </div>
      )}

      {/* Run status indicator badge */}
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
        style={{ backgroundColor: `${color}20` }}
      >
        <Icon className="h-4 w-4" style={{ color }} />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium leading-tight truncate max-w-30">{label}</p>
        <p className="text-[10px] text-muted-foreground leading-tight">{sublabel}</p>
      </div>
    </>
  );
}
