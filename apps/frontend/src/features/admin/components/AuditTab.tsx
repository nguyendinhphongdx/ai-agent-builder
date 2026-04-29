"use client";

import { ClipboardList, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAdminAudit } from "../hooks/useAdmin";

export function AuditTab() {
  const { data, isLoading } = useAdminAudit({ limit: 100 });

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }
  if (!data || data.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-border bg-card py-12 text-center text-xs text-muted-foreground">
        No admin actions logged yet.
      </p>
    );
  }

  return (
    <div className="space-y-1">
      {data.map((row) => (
        <div
          key={row.id}
          className="flex items-start gap-3 rounded-lg border border-border bg-card p-3"
        >
          <ClipboardList className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="text-[10px] font-mono">
                {row.action}
              </Badge>
              <span className="text-xs">
                by{" "}
                <span className="font-medium">{row.actor_email ?? "(deleted)"}</span>
              </span>
              {row.target_type && (
                <span className="text-[10px] text-muted-foreground">
                  → {row.target_type}:{" "}
                  <span className="font-mono">{row.target_id}</span>
                </span>
              )}
            </div>
            {Object.keys(row.details).length > 0 && (
              <pre className="mt-1 overflow-x-auto rounded bg-muted/40 p-1.5 text-[10px] font-mono text-muted-foreground">
                {JSON.stringify(row.details, null, 2)}
              </pre>
            )}
            <p className="mt-1 text-[10px] text-muted-foreground/70">
              {new Date(row.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
