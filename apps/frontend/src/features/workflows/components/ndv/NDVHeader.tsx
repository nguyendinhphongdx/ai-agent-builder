"use client";

import { createElement } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Pin,
  PinOff,
  Play,
  X,
  XCircle,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { NodeTypeDefinition } from "../../nodes/types";
import type { NodeRunStatus } from "../../types";
import { cn } from "@/lib/utils";

interface NDVHeaderProps {
  definition: NodeTypeDefinition;
  label: string;
  onClose: () => void;
  status?: NodeRunStatus;
  durationMs?: number;
  tokensUsed?: number;

  // Execute step
  onExecuteStep?: () => void;
  isExecuting?: boolean;
  executeDisabledReason?: string;

  // Pin output
  isPinned?: boolean;
  onTogglePin?: () => void;
  pinDisabledReason?: string;
}

export function NDVHeader({
  definition,
  label,
  onClose,
  status,
  durationMs,
  tokensUsed,
  onExecuteStep,
  isExecuting = false,
  executeDisabledReason,
  isPinned = false,
  onTogglePin,
  pinDisabledReason,
}: NDVHeaderProps) {
  const Icon = definition.icon;

  return (
    <div className="flex items-center justify-between border-b border-border bg-background px-4 py-2.5">
      <div className="flex items-center gap-3">
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back</span>
        </button>

        <div className="h-4 w-px bg-border" />

        <div className="flex items-center gap-2">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${definition.color}20` }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color: definition.color }} />
          </div>
          <span className="text-sm font-medium">{label || definition.label}</span>
        </div>

        {status && <StatusPill status={status} />}

        {(durationMs !== undefined || (tokensUsed && tokensUsed > 0)) && (
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            {durationMs !== undefined && <span>{formatDuration(durationMs)}</span>}
            {tokensUsed && tokensUsed > 0 && (
              <span className="flex items-center gap-1">
                <Zap className="h-3 w-3" />
                {tokensUsed.toLocaleString()}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-1">
        {onTogglePin && (
          <Button
            variant={isPinned ? "secondary" : "ghost"}
            size="sm"
            className="gap-1.5"
            onClick={onTogglePin}
            disabled={!isPinned && !!pinDisabledReason}
            title={
              isPinned
                ? "Unpin output"
                : pinDisabledReason ?? "Pin current output to skip executor on full runs"
            }
          >
            {isPinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
            {isPinned ? "Pinned" : "Pin"}
          </Button>
        )}

        {onExecuteStep && (
          <Button
            variant="default"
            size="sm"
            className="gap-1.5"
            onClick={onExecuteStep}
            disabled={isExecuting || !!executeDisabledReason}
            title={executeDisabledReason ?? "Run only this node (⌘+Enter)"}
          >
            {isExecuting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Execute step
          </Button>
        )}

        <button
          onClick={onClose}
          className="ml-1 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: NodeRunStatus }) {
  const meta = STATUS_META[status];
  return (
    <span
      className={cn(
        "flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
        meta.className,
      )}
    >
      {createElement(meta.icon, { className: cn("h-3 w-3", meta.iconClass) })}
      {meta.label}
    </span>
  );
}

const STATUS_META: Record<
  NodeRunStatus,
  {
    label: string;
    className: string;
    icon: typeof CheckCircle2;
    iconClass?: string;
  }
> = {
  completed: {
    label: "Completed",
    className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
    icon: CheckCircle2,
  },
  failed: {
    label: "Failed",
    className: "border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300",
    icon: XCircle,
  },
  running: {
    label: "Running",
    className: "border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300",
    icon: Loader2,
    iconClass: "animate-spin",
  },
  skipped: {
    label: "Skipped",
    className: "border-border bg-muted text-muted-foreground",
    icon: XCircle,
  },
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}m ${s}s`;
}
