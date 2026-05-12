"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  kbConnectorsService,
  type KBConnector,
} from "@/lib/api/kbConnectorsService";
import {
  findProvider,
  type ConnectorProvider,
} from "../../data/connectorProviders";
import { ConnectorForm } from "./ConnectorForm";
import { ConnectorPicker } from "./ConnectorPicker";

type View = { kind: "list" } | { kind: "picker" } | { kind: "form"; provider: ConnectorProvider };

/**
 * "Connectors" tab on a KB. Three views (state machine):
 *   list   → existing connectors + "+ Add" button
 *   picker → 10 provider cards (ConnectorPicker)
 *   form   → provider-specific create form (ConnectorForm)
 *
 * The form auto-returns to ``list`` on success so the user sees
 * their fresh connector + can fire "Sync now".
 */
export function ConnectorsTab({ kbId }: { kbId: string }) {
  const [view, setView] = useState<View>({ kind: "list" });

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-border px-6 py-4">
        <h1 className="text-sm font-semibold">Connectors</h1>
        <p className="mt-0.5 text-[11px] text-muted-foreground">
          Sync documents from external sources. Each connector pulls new /
          changed items into this knowledge base on its own cadence.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        {view.kind === "list" && (
          <ConnectorList
            kbId={kbId}
            onAdd={() => setView({ kind: "picker" })}
          />
        )}
        {view.kind === "picker" && (
          <ConnectorPicker
            onSelect={(p) => setView({ kind: "form", provider: p })}
          />
        )}
        {view.kind === "form" && (
          <ConnectorForm
            kbId={kbId}
            provider={view.provider}
            onBack={() => setView({ kind: "picker" })}
            onCreated={() => setView({ kind: "list" })}
          />
        )}
      </div>
    </div>
  );
}

/* ─── List view ─────────────────────────────────────────────── */

function ConnectorList({
  kbId,
  onAdd,
}: {
  kbId: string;
  onAdd: () => void;
}) {
  const qc = useQueryClient();
  const listQ = useQuery({
    queryKey: ["kb-connectors", kbId],
    queryFn: () => kbConnectorsService.list(kbId),
  });

  const sync = useMutation({
    mutationFn: (id: string) => kbConnectorsService.syncNow(kbId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kb-connectors", kbId] }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => kbConnectorsService.remove(kbId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kb-connectors", kbId] }),
  });

  const toggle = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      kbConnectorsService.update(kbId, id, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kb-connectors", kbId] }),
  });

  if (listQ.isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  const items = listQ.data ?? [];

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center">
        <h2 className="text-sm font-semibold">No connectors yet</h2>
        <p className="mt-1 max-w-md text-[12px] text-muted-foreground">
          Connect S3, Google Drive, Notion, Confluence, SharePoint, Dropbox,
          and more. New items sync automatically.
        </p>
        <Button onClick={onAdd} className="mt-4">
          <Plus className="mr-1 h-3.5 w-3.5" /> Add connector
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground">
          {items.length} connector{items.length === 1 ? "" : "s"}
        </span>
        <Button onClick={onAdd} size="sm">
          <Plus className="mr-1 h-3.5 w-3.5" /> Add connector
        </Button>
      </div>
      <ul className="divide-y divide-border rounded-xl border border-border bg-card">
        {items.map((c) => (
          <ConnectorRow
            key={c.id}
            connector={c}
            syncing={sync.isPending && sync.variables === c.id}
            onSync={() => sync.mutate(c.id)}
            onToggle={(active) =>
              toggle.mutate({ id: c.id, is_active: active })
            }
            onDelete={() => {
              if (window.confirm(`Delete "${c.name}"? Documents already synced stay in the KB.`)) {
                remove.mutate(c.id);
              }
            }}
          />
        ))}
      </ul>
    </div>
  );
}

function ConnectorRow({
  connector: c,
  syncing,
  onSync,
  onToggle,
  onDelete,
}: {
  connector: KBConnector;
  syncing: boolean;
  onSync: () => void;
  onToggle: (active: boolean) => void;
  onDelete: () => void;
}) {
  const provider = findProvider(c.connector_type);

  return (
    <li className="flex items-start justify-between gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{c.name}</span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
              c.is_active
                ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
                : "bg-muted/60 text-muted-foreground",
            )}
          >
            {c.is_active ? "active" : "off"}
          </span>
        </div>
        <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
          {provider?.label ?? c.connector_type}
        </div>
        <div className="mt-1 flex items-center gap-3 text-[11px] text-muted-foreground">
          {c.last_sync_at ? (
            <span className="inline-flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              Last sync {timeAgo(c.last_sync_at)}
            </span>
          ) : (
            <span>Never synced</span>
          )}
          {c.last_error && (
            <span className="inline-flex items-center gap-1 text-rose-600">
              <AlertTriangle className="h-3 w-3" />
              {truncate(c.last_error, 80)}
            </span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <label className="inline-flex cursor-pointer items-center gap-1.5 text-[11px] text-muted-foreground">
          <input
            type="checkbox"
            checked={c.is_active}
            onChange={(e) => onToggle(e.target.checked)}
            className="h-3 w-3 accent-primary"
          />
          Active
        </label>
        <button
          type="button"
          onClick={onSync}
          disabled={!c.is_active || syncing}
          className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] hover:bg-accent disabled:opacity-50"
        >
          <RefreshCw className={cn("h-3 w-3", syncing && "animate-spin")} />
          Sync now
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label="Delete connector"
          className="rounded-md p-1 text-muted-foreground hover:bg-rose-500/10 hover:text-rose-600"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </li>
  );
}

/* ─── Helpers ──────────────────────────────────────────────── */

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const sec = Math.max(1, Math.floor((now - then) / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function truncate(s: string, max: number): string {
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}
