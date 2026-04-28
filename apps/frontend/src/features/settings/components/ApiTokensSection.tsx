"use client";

import { useEffect, useState, useCallback } from "react";
import { Key, Loader2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  personalTokenService,
  type PersonalToken,
} from "@/lib/api/personalTokenService";
import { CreateApiTokenDialog } from "./CreateApiTokenDialog";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function ApiTokensSection() {
  const [tokens, setTokens] = useState<PersonalToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTokens(await personalTokenService.list());
    } catch {
      setTokens([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRevoke = async (id: string) => {
    if (!confirm("Revoke this token? Apps using it will lose access immediately.")) return;
    setRevokingId(id);
    try {
      await personalTokenService.revoke(id);
      await load();
    } finally {
      setRevokingId(null);
    }
  };

  const isActive = (t: PersonalToken) =>
    t.revoked_at === null &&
    (t.expires_at === null || new Date(t.expires_at) > new Date());

  return (
    <section>
      <div className="mb-4 flex items-start justify-between">
        <div>
          <h2 className="text-base font-semibold">API Tokens</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Long-lived tokens for external scripts/apps to call AgentForge on your behalf.
            Use header <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">Authorization: Bearer afpt_…</code>.
          </p>
        </div>
        <Button size="sm" className="gap-1.5" onClick={() => setCreateOpen(true)}>
          <Plus className="h-3.5 w-3.5" />
          New token
        </Button>
      </div>

      {loading ? (
        <div className="flex h-24 items-center justify-center text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : tokens.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 py-10 text-center">
          <Key className="mb-2 h-6 w-6 text-muted-foreground/40" />
          <p className="text-sm font-medium">Chưa có token nào</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Click "New token" để tạo cái đầu tiên.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left font-semibold">Name</th>
                <th className="px-3 py-2 text-left font-semibold">Prefix</th>
                <th className="px-3 py-2 text-left font-semibold">Scopes</th>
                <th className="px-3 py-2 text-left font-semibold">Last used</th>
                <th className="px-3 py-2 text-left font-semibold">Status</th>
                <th className="w-12 px-3 py-2 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {tokens.map((t) => {
                const active = isActive(t);
                return (
                  <tr
                    key={t.id}
                    className={cn(
                      "border-t border-border/60",
                      !active && "opacity-60",
                    )}
                  >
                    <td className="px-3 py-2.5 font-medium">{t.name}</td>
                    <td className="px-3 py-2.5 font-mono text-[11px]">
                      {t.key_prefix}•••
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex flex-wrap gap-1">
                        {t.scopes.map((s) => (
                          <Badge
                            key={s}
                            variant="secondary"
                            className="px-1.5 py-0 font-mono text-[9px]"
                          >
                            {s}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">
                      {formatDate(t.last_used_at)}
                    </td>
                    <td className="px-3 py-2.5">
                      {t.revoked_at ? (
                        <Badge variant="outline" className="text-[10px]">
                          Revoked
                        </Badge>
                      ) : t.expires_at && new Date(t.expires_at) <= new Date() ? (
                        <Badge variant="outline" className="text-[10px]">
                          Expired
                        </Badge>
                      ) : (
                        <Badge
                          variant="secondary"
                          className="bg-emerald-500/15 text-[10px] text-emerald-700 dark:text-emerald-400"
                        >
                          Active
                        </Badge>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {active && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-destructive"
                          disabled={revokingId === t.id}
                          onClick={() => handleRevoke(t.id)}
                          title="Revoke token"
                        >
                          {revokingId === t.id ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="h-3.5 w-3.5" />
                          )}
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <CreateApiTokenDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={load}
      />
    </section>
  );
}
