"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  oauthConnectorsService,
  type OAuthConnection,
} from "@/lib/api/oauthConnectorsService";
import { OAUTH_CONNECTIONS_QUERY_KEY } from "../hooks/useOAuthConnections";

interface ConnectionRowProps {
  connection: OAuthConnection;
  /** Optional label override for providers whose ``account_label``
   *  is sparse (Notion + Dropbox return cryptic ids). */
  providerLabel?: string;
}

/**
 * One connection card — provider name, the workspace/account it's
 * authorised against, when it was wired, and a Disconnect button.
 *
 * Disconnect is destructive: any KB connector / agent that points
 * at this connection will start erroring "OAuth: connection not
 * found" on the next sync, so we ``window.confirm`` first.
 */
export function ConnectionRow({ connection: c, providerLabel }: ConnectionRowProps) {
  const qc = useQueryClient();
  const remove = useMutation({
    mutationFn: () => oauthConnectorsService.remove(c.id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: OAUTH_CONNECTIONS_QUERY_KEY }),
  });

  const accountText =
    c.account_label || c.external_account_id || "Connected account";

  const onDelete = () => {
    if (
      window.confirm(
        `Disconnect ${providerLabel ?? c.provider} — "${accountText}"? ` +
          "KB connectors using it will start failing on the next sync.",
      )
    ) {
      remove.mutate();
    }
  };

  return (
    <li className="flex items-start justify-between gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {providerLabel ?? c.provider}
          </span>
          <span className="rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
            connected
          </span>
        </div>
        <div className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground">
          {accountText}
        </div>
        <div className="mt-1 flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <CheckCircle2 className="h-3 w-3" />
            Linked {formatDate(c.created_at)}
          </span>
          {c.expires_at && (
            <span className="text-amber-600 dark:text-amber-400">
              Token expires {formatDate(c.expires_at)}
            </span>
          )}
          {c.scope && (
            <span className="truncate" title={c.scope}>
              scope: {c.scope.length > 40 ? c.scope.slice(0, 40) + "…" : c.scope}
            </span>
          )}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1.5">
        <button
          type="button"
          onClick={onDelete}
          disabled={remove.isPending}
          aria-label="Disconnect"
          className={cn(
            "rounded-md p-1 text-muted-foreground hover:bg-rose-500/10 hover:text-rose-600",
            remove.isPending && "opacity-50",
          )}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </li>
  );
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
