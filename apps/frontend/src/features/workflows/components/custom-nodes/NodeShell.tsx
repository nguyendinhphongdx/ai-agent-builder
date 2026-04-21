"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import type { NodeRunStatus } from "../../stores/workflowEditorStore";

interface NodeShellProps {
  shape?: string;
  selected?: boolean;
  runStatus?: NodeRunStatus;
  children: ReactNode;
}

/**
 * Visual shell of a node: border, ring, shape, running beam animation.
 * Purely presentational - no handles, no data.
 */
export function NodeShell({
  shape = "rounded-xl",
  selected,
  runStatus,
  children,
}: NodeShellProps) {
  return (
    <>
      {/* Running border beam overlay */}
      {runStatus === "running" && (
        <span
          aria-hidden
          className={cn(
            "pointer-events-none absolute -inset-px animate-border-spin",
            shape,
          )}
          style={{
            background:
              "conic-gradient(from var(--border-angle), transparent 0deg, transparent 270deg, var(--primary) 340deg, transparent 360deg)",
            WebkitMask:
              "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
            WebkitMaskComposite: "xor",
            mask: "linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)",
            maskComposite: "exclude",
            padding: "2px",
          }}
        />
      )}

      <div
        className={cn(
          "relative flex items-center gap-2.5 border bg-card px-4 py-3 shadow-sm min-w-35",
          shape,
          selected
            ? "border-primary ring-2 ring-primary/20"
            : runStatus === "failed"
              ? "border-destructive ring-2 ring-destructive/20"
              : runStatus === "completed"
                ? "border-emerald-500 ring-2 ring-emerald-500/20"
                : runStatus === "running"
                  ? "border-primary/40"
                  : "border-border",
        )}
      >
        {children}
      </div>
    </>
  );
}
