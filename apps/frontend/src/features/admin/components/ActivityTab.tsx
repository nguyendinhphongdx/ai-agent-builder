"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  auditService,
  type AuditLogRow,
  type AuditListParams,
} from "@/lib/api/auditService";

const PAGE_SIZE = 50;
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

/**
 * Cross-tenant activity log (the broader audit_logs table, distinct
 * from the existing /admin/audit staff-actions surface).
 *
 * Filter UI is intentionally minimal — action_prefix is the killer
 * one ("workspace.member." surfaces every membership event without
 * picking one). Date range + actor pinning come up on first triage.
 */
export function ActivityTab() {
  const [filter, setFilter] = useState<AuditListParams>({
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [actionPrefix, setActionPrefix] = useState("");
  const [actor, setActor] = useState("");

  // Apply form fields → query params only on debounce-like nudge (Enter or blur).
  const apply = (overrides: Partial<AuditListParams> = {}) =>
    setFilter((prev) => ({
      ...prev,
      action_prefix: actionPrefix || undefined,
      actor_user_id: actor || undefined,
      offset: 0,
      ...overrides,
    }));

  const { data, isFetching } = useQuery({
    queryKey: ["admin-activity", filter],
    queryFn: () => auditService.listAdmin(filter),
    placeholderData: (prev) => prev,
  });

  const rows = data ?? [];
  const csvHref = useMemo(
    () =>
      auditService.csvUrl(API_BASE, { ...filter, limit: undefined, offset: 0 }),
    [filter],
  );

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-2 rounded-lg border border-border bg-card p-3 md:grid-cols-[1fr_1fr_auto]">
        <div className="space-y-1">
          <Label htmlFor="action-prefix" className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Action prefix
          </Label>
          <Input
            id="action-prefix"
            value={actionPrefix}
            onChange={(e) => setActionPrefix(e.target.value)}
            onBlur={() => apply()}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            placeholder="e.g. workspace.member."
            className="h-8 font-mono text-[11px]"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="actor" className="text-[10px] uppercase tracking-wider text-muted-foreground">
            Actor user id
          </Label>
          <Input
            id="actor"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            onBlur={() => apply()}
            onKeyDown={(e) => e.key === "Enter" && apply()}
            placeholder="UUID"
            className="h-8 font-mono text-[11px]"
          />
        </div>
        <div className="flex items-end gap-2">
          <Button
            size="sm"
            variant="outline"
            asChild
          >
            <a href={csvHref}>
              <Download className="mr-1.5 h-3 w-3" />
              CSV
            </a>
          </Button>
        </div>
      </div>

      {isFetching && rows.length === 0 ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : rows.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-card py-12 text-center text-xs text-muted-foreground">
          No activity matches the current filters.
        </p>
      ) : (
        <div className="space-y-1">
          {rows.map((row) => (
            <ActivityRow key={row.id} row={row} />
          ))}
        </div>
      )}

      {/* Pagination — newer-then-older */}
      <div className="flex items-center justify-between pt-2 text-[11px] text-muted-foreground">
        <span>
          Showing {rows.length} row{rows.length === 1 ? "" : "s"}
          {filter.offset ? ` from offset ${filter.offset}` : ""}
        </span>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="ghost"
            disabled={!filter.offset}
            onClick={() =>
              setFilter((p) => ({ ...p, offset: Math.max(0, (p.offset ?? 0) - PAGE_SIZE) }))
            }
          >
            ← Newer
          </Button>
          <Button
            size="sm"
            variant="ghost"
            disabled={rows.length < PAGE_SIZE}
            onClick={() =>
              setFilter((p) => ({ ...p, offset: (p.offset ?? 0) + PAGE_SIZE }))
            }
          >
            Older →
          </Button>
        </div>
      </div>
    </div>
  );
}

function ActivityRow({ row }: { row: AuditLogRow }) {
  const hasMetadata = Object.keys(row.data || {}).length > 0;
  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-card p-3 text-xs">
      <div className="min-w-0 flex-1 space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="text-[10px] font-mono">
            {row.action}
          </Badge>
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {row.actor_type}
          </span>
          <span className="text-[10px] text-muted-foreground">
            {new Date(row.created_at).toLocaleString()}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
          {row.actor_user_id && (
            <span>
              actor: <code className="font-mono">{row.actor_user_id.slice(0, 8)}…</code>
            </span>
          )}
          {row.resource_type && (
            <span>
              {row.resource_type}:{" "}
              <code className="font-mono">{(row.resource_id ?? "").slice(0, 8)}…</code>
            </span>
          )}
          {row.workspace_id && (
            <span>
              ws: <code className="font-mono">{row.workspace_id.slice(0, 8)}…</code>
            </span>
          )}
          {row.ip_address && <span>ip: {row.ip_address}</span>}
        </div>
        {hasMetadata && (
          <pre className="mt-1 overflow-x-auto rounded bg-muted/40 p-1.5 text-[10px] font-mono text-muted-foreground">
            {JSON.stringify(row.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
