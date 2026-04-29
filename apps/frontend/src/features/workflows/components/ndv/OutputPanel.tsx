"use client";

import { AlertTriangle, FileOutput } from "lucide-react";
import { DataView } from "./DataView";

interface OutputPanelProps {
  items: Record<string, unknown>[] | null;
  state?: "no-run" | "not-reached" | "running" | "ready";
  error?: string | null;
}

export function OutputPanel({ items, state = "no-run", error }: OutputPanelProps) {
  if (error) {
    return (
      <div className="flex h-full flex-col">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
          <FileOutput className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-semibold text-muted-foreground tracking-wider">OUTPUT</span>
        </div>
        <div className="flex flex-1 items-start gap-3 p-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-red-500" />
          <div className="min-w-0 space-y-1.5">
            <p className="text-xs font-medium text-red-600 dark:text-red-400">Node failed</p>
            <pre className="whitespace-pre-wrap break-words text-[11px] text-muted-foreground font-mono">
              {error}
            </pre>
          </div>
        </div>
      </div>
    );
  }

  const empty = describeEmpty(state);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        <FileOutput className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold text-muted-foreground tracking-wider">OUTPUT</span>
      </div>
      <DataView
        items={items ?? []}
        emptyIcon={<FileOutput className="h-5 w-5 text-muted-foreground" />}
        emptyTitle={empty.title}
        emptyDescription={empty.description}
      />
    </div>
  );
}

function describeEmpty(state: NonNullable<OutputPanelProps["state"]>) {
  switch (state) {
    case "running":
      return { title: "Running…", description: "Waiting for this node to finish." };
    case "not-reached":
      return {
        title: "Node not reached",
        description: "Upstream nodes did not route execution here on the last run.",
      };
    case "ready":
      return {
        title: "No output items",
        description: "This node completed without producing any data.",
      };
    case "no-run":
    default:
      return {
        title: "No output data yet",
        description: "Execute the workflow to see output data.",
      };
  }
}
