"use client";

import { FileInput } from "lucide-react";
import { DataView } from "./DataView";

interface InputPanelProps {
  items: Record<string, unknown>[] | null;
  /** Empty-state hint when items is null/empty. */
  state?: "no-run" | "not-reached" | "ready";
}

export function InputPanel({ items, state = "no-run" }: InputPanelProps) {
  const empty = describeEmpty(state);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        <FileInput className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold text-muted-foreground tracking-wider">INPUT</span>
      </div>
      <DataView
        items={items ?? []}
        emptyIcon={<FileInput className="h-5 w-5 text-muted-foreground" />}
        emptyTitle={empty.title}
        emptyDescription={empty.description}
      />
    </div>
  );
}

function describeEmpty(state: NonNullable<InputPanelProps["state"]>) {
  switch (state) {
    case "not-reached":
      return {
        title: "Node not reached",
        description: "Upstream nodes did not route execution here on the last run.",
      };
    case "ready":
      return {
        title: "No input items",
        description: "This node executed without any incoming data.",
      };
    case "no-run":
    default:
      return {
        title: "No input data yet",
        description: "Execute the workflow to see input data.",
      };
  }
}
