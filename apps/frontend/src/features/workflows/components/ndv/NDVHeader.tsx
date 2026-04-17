"use client";

import { createElement } from "react";
import { ArrowLeft, X } from "lucide-react";
import type { NodeTypeDefinition } from "../../nodes/types";

interface NDVHeaderProps {
  definition: NodeTypeDefinition;
  label: string;
  onClose: () => void;
}

export function NDVHeader({ definition, label, onClose }: NDVHeaderProps) {
  const Icon = definition.icon;

  return (
    <div className="flex items-center justify-between border-b border-border bg-background px-4 py-2.5">
      <div className="flex items-center gap-3">
        {/* Back to canvas */}
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Back</span>
        </button>

        {/* Divider */}
        <div className="h-4 w-px bg-border" />

        {/* Node icon + name */}
        <div className="flex items-center gap-2">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ backgroundColor: `${definition.color}20` }}
          >
            <Icon className="h-3.5 w-3.5" style={{ color: definition.color }} />
          </div>
          <span className="text-sm font-medium">{label || definition.label}</span>
        </div>
      </div>

      {/* Close */}
      <button
        onClick={onClose}
        className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
