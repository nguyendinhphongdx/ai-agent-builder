"use client";

import { StatusBadge } from "@/components/ui/status-badge";
import { DeleteIconButton } from "./DeleteIconButton";

/**
 * Identical chrome around every trigger row — header line with name +
 * active badge, mono-style config summary slot, optional error line,
 * and the delete icon. Providers only supply the summary line content.
 */
export function TriggerRowFrame({
  name,
  active,
  summary,
  lastError,
  onDelete,
}: {
  name: string;
  active: boolean;
  summary: React.ReactNode;
  lastError?: string | null;
  onDelete: () => void;
}) {
  return (
    <li className="flex items-center justify-between px-5 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm font-medium">
          <span className="truncate">{name}</span>
          <StatusBadge tone={active ? "active" : "inactive"}>
            {active ? "active" : "off"}
          </StatusBadge>
        </div>
        <div className="mt-0.5 truncate font-mono text-[11px] text-muted-foreground">
          {summary}
        </div>
        {lastError && (
          <div className="mt-0.5 text-[11px] text-destructive">
            ⚠ {lastError}
          </div>
        )}
      </div>
      <DeleteIconButton onClick={onDelete} />
    </li>
  );
}
