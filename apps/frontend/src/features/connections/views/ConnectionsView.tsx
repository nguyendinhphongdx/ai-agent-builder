"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { OAuthConnection } from "@/lib/api/oauthConnectorsService";
import { ConnectButton } from "../components/ConnectButton";
import { ConnectionRow } from "../components/ConnectionRow";
import {
  OAUTH_CONNECTIONS_QUERY_KEY,
  useOAuthConnections,
  useOAuthProviders,
} from "../hooks/useOAuthConnections";

/**
 * Settings → Connections page. One list of every OAuth provider
 * configured on the deployment, with the connected accounts (if
 * any) grouped under each one. Connect / Disconnect actions live
 * inline; no separate "create" form because OAuth IS the form.
 *
 * Handles the post-callback redirect: the BE bounces back with
 * ``?oauth=success&connection_id=...&provider=...`` (or
 * ``?error=...``) — we read those, show a banner, and strip them
 * from the URL so a refresh doesn't re-show the toast.
 */
export function ConnectionsView() {
  const params = useSearchParams();
  const router = useRouter();
  const qc = useQueryClient();

  const providersQ = useOAuthProviders();
  const connectionsQ = useOAuthConnections();

  const [banner, setBanner] = useState<
    | { kind: "success"; provider: string; connectionId: string }
    | { kind: "error"; message: string }
    | null
  >(null);

  // ──────────────────────────────────────────────────────────────
  // Read callback params on mount + clear them from the URL.
  useEffect(() => {
    const oauth = params.get("oauth");
    const error = params.get("error");
    if (oauth === "success") {
      setBanner({
        kind: "success",
        provider: params.get("provider") || "",
        connectionId: params.get("connection_id") || "",
      });
      qc.invalidateQueries({ queryKey: OAUTH_CONNECTIONS_QUERY_KEY });
      router.replace("/settings/connections");
    } else if (error) {
      setBanner({ kind: "error", message: error });
      router.replace("/settings/connections");
    }
    // ``params`` is a stable reference but we only want this on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, OAuthConnection[]>();
    for (const c of connectionsQ.data ?? []) {
      const list = map.get(c.provider) ?? [];
      list.push(c);
      map.set(c.provider, list);
    }
    return map;
  }, [connectionsQ.data]);

  if (providersQ.isLoading || connectionsQ.isLoading) {
    return (
      <div className="flex items-center justify-center p-12 text-muted-foreground">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  const providers = providersQ.data ?? [];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-base font-semibold">Connections</h1>
        <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
          Authorise this workspace against external services once — then
          reuse the connection across KB connectors, agents, and tools.
          Tokens are encrypted at rest and refreshed automatically.
        </p>
      </header>

      {banner?.kind === "success" && (
        <div className="flex items-center gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 className="h-4 w-4" />
          Connected {banner.provider || "successfully"}. You can now wire it
          into a KB connector or agent.
        </div>
      )}
      {banner?.kind === "error" && (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-300">
          OAuth failed: {banner.message}
        </div>
      )}

      <div className="space-y-3">
        {providers.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
            No OAuth providers wired on this deployment yet. An admin needs
            to set the client id / secret env vars (see backend docs).
          </div>
        ) : (
          providers.map((p) => {
            const connections = grouped.get(p.id) ?? [];
            return (
              <section
                key={p.id}
                className={cn(
                  "overflow-hidden rounded-xl border border-border bg-card",
                  !p.configured && "opacity-60",
                )}
              >
                <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
                  <div>
                    <h2 className="text-sm font-semibold">{p.label}</h2>
                    {!p.configured && (
                      <p className="mt-0.5 text-[10px] text-muted-foreground">
                        Not configured — admin must wire client id / secret.
                      </p>
                    )}
                    {p.configured && connections.length === 0 && (
                      <p className="mt-0.5 text-[10px] text-muted-foreground">
                        No connections yet.
                      </p>
                    )}
                  </div>
                  <ConnectButton
                    provider={p.id}
                    label={p.label}
                    configured={p.configured}
                  />
                </header>
                {connections.length > 0 && (
                  <ul className="divide-y divide-border">
                    {connections.map((c) => (
                      <ConnectionRow
                        key={c.id}
                        connection={c}
                        providerLabel={p.label}
                      />
                    ))}
                  </ul>
                )}
              </section>
            );
          })
        )}
      </div>
    </div>
  );
}
