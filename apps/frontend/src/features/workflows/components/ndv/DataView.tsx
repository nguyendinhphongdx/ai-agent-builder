"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

type ViewMode = "schema" | "table" | "json";

interface DataViewProps {
  items: Record<string, unknown>[];
  emptyIcon: React.ReactNode;
  emptyTitle: string;
  emptyDescription: string;
}

export function DataView({ items, emptyIcon, emptyTitle, emptyDescription }: DataViewProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("table");

  if (!items || items.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-4">
        <div className="text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-muted">
            {emptyIcon}
          </div>
          <p className="text-xs font-medium text-muted-foreground">{emptyTitle}</p>
          <p className="mt-1 text-[10px] text-muted-foreground/70">{emptyDescription}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* View mode tabs */}
      <div className="flex items-center gap-1 border-b border-border px-3 py-1.5">
        {(["schema", "table", "json"] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setViewMode(mode)}
            className={cn(
              "rounded-md px-2.5 py-1 text-[10px] font-medium capitalize transition-colors",
              viewMode === mode
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-foreground"
            )}
          >
            {mode === "json" ? "JSON" : mode.charAt(0).toUpperCase() + mode.slice(1)}
          </button>
        ))}
        <span className="ml-auto text-[10px] text-muted-foreground">
          {items.length} item{items.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {viewMode === "schema" && <SchemaView items={items} />}
        {viewMode === "table" && <TableView items={items} />}
        {viewMode === "json" && <JsonView items={items} />}
      </div>
    </div>
  );
}

// ─── Schema View ──────────────────────────────────────────────────

function SchemaView({ items }: { items: Record<string, unknown>[] }) {
  const sample = items[0] || {};
  const fields = Object.entries(sample).map(([key, value]) => ({
    key,
    type: getValueType(value),
    preview: getPreview(value),
  }));

  return (
    <div className="p-3 space-y-1">
      {fields.map((field) => (
        <div key={field.key} className="flex items-start gap-2 rounded-md border border-border bg-muted/30 px-3 py-2">
          <span className="text-xs font-medium text-foreground">{field.key}</span>
          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
            {field.type}
          </span>
          {field.preview && (
            <span className="ml-auto truncate text-[10px] text-muted-foreground max-w-48">
              {field.preview}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

// ─── Table View ───────────────────────────────────────────────────

function TableView({ items }: { items: Record<string, unknown>[] }) {
  const columns = items.length > 0 ? Object.keys(items[0]) : [];

  return (
    <div className="overflow-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="px-3 py-1.5 text-left font-medium text-muted-foreground w-8">#</th>
            {columns.map((col) => (
              <th key={col} className="px-3 py-1.5 text-left font-medium text-muted-foreground">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-border hover:bg-muted/30">
              <td className="px-3 py-1.5 text-muted-foreground">{i}</td>
              {columns.map((col) => (
                <td key={col} className="px-3 py-1.5 max-w-64 truncate">
                  {formatCellValue(item[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── JSON View ────────────────────────────────────────────────────

function JsonView({ items }: { items: Record<string, unknown>[] }) {
  return (
    <pre className="p-3 text-[11px] font-mono text-foreground/80 overflow-auto whitespace-pre-wrap break-words">
      {JSON.stringify(items, null, 2)}
    </pre>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────

function getValueType(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function getPreview(value: unknown): string {
  if (value === null || value === undefined) return "null";
  if (typeof value === "string") return value.length > 50 ? value.slice(0, 50) + "..." : value;
  if (typeof value === "object") return JSON.stringify(value).slice(0, 50) + "...";
  return String(value);
}

function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value).slice(0, 100);
  return String(value);
}
