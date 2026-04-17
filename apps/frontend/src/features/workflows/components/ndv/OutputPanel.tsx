"use client";

import { FileOutput } from "lucide-react";
import { DataView } from "./DataView";

interface OutputPanelProps {
  items: Record<string, unknown>[];
}

export function OutputPanel({ items }: OutputPanelProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        <FileOutput className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold text-muted-foreground tracking-wider">OUTPUT</span>
      </div>
      <DataView
        items={items}
        emptyIcon={<FileOutput className="h-5 w-5 text-muted-foreground" />}
        emptyTitle="No output data yet"
        emptyDescription="Execute the workflow to see output data"
      />
    </div>
  );
}
