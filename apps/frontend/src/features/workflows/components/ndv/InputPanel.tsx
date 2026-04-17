"use client";

import { FileInput } from "lucide-react";
import { DataView } from "./DataView";

interface InputPanelProps {
  items: Record<string, unknown>[];
}

export function InputPanel({ items }: InputPanelProps) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        <FileInput className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold text-muted-foreground tracking-wider">INPUT</span>
      </div>
      <DataView
        items={items}
        emptyIcon={<FileInput className="h-5 w-5 text-muted-foreground" />}
        emptyTitle="No input data yet"
        emptyDescription="Execute the workflow to see input data"
      />
    </div>
  );
}
