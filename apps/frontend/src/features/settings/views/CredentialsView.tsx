"use client";

import { useCallback, useEffect, useState } from "react";
import { Key, Loader2, Plus, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConnectCredentialDialog } from "@/features/agents/components/editor/ConnectCredentialDialog";
import { useModelCatalog } from "@/lib/models/catalog";
import {
  aiCredentialService,
  type AICredentialResponse,
} from "@/lib/api/aiCredentialService";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "../components/SettingsPrimitives";

/**
 * Per-provider AI credential management. Keys are encrypted at rest via
 * Fernet and never returned to the browser in plaintext — the masked
 * preview comes from the server.
 */
export function CredentialsView() {
  const { data: catalog } = useModelCatalog();
  const providers = catalog?.providers ?? [];

  const [credentials, setCredentials] = useState<AICredentialResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectProvider, setConnectProvider] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setCredentials(await aiCredentialService.list());
    } catch {
      setCredentials([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await aiCredentialService.remove(id);
      setCredentials((prev) => prev.filter((c) => c.id !== id));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div>
      <SettingsPageHeader
        title="AI Credentials"
        description="One key per provider. Keys are encrypted at rest and never returned to the browser in plaintext."
      />

      {loading ? (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : (
        <SettingsStack>
          {providers.map((provider) => {
            const providerCreds = credentials.filter(
              (c) => c.provider === provider.id,
            );
            return (
              <SettingsCard
                key={provider.id}
                title={provider.label}
                description={provider.description}
                action={
                  <Button
                    onClick={() => setConnectProvider(provider.id)}
                    variant="outline"
                    size="sm"
                    className="gap-1.5 text-xs"
                  >
                    <Plus className="h-3 w-3" />
                    Add credential
                  </Button>
                }
                bodyClassName={providerCreds.length > 0 ? "p-0" : undefined}
              >
                {providerCreds.length > 0 ? (
                  <ul className="divide-y divide-border">
                    {providerCreds.map((c) => (
                      <li
                        key={c.id}
                        className="flex items-center gap-3 px-5 py-3"
                      >
                        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-muted">
                          <Key className="h-3.5 w-3.5 text-muted-foreground" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-xs font-medium">{c.name}</p>
                          <code className="font-mono text-[10px] text-muted-foreground">
                            {c.masked_key}
                          </code>
                        </div>
                        {c.last_used_at && (
                          <Badge
                            variant="secondary"
                            className="h-4 px-1 text-[9px]"
                          >
                            used
                          </Badge>
                        )}
                        <button
                          onClick={() => handleDelete(c.id)}
                          disabled={deletingId === c.id}
                          className="text-muted-foreground/60 transition-colors hover:text-destructive disabled:opacity-50"
                          title="Delete credential"
                        >
                          {deletingId === c.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Trash2 className="h-3 w-3" />
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[11px] text-muted-foreground">
                    No credentials for {provider.label} yet.
                  </p>
                )}
              </SettingsCard>
            );
          })}
        </SettingsStack>
      )}

      {connectProvider && (
        <ConnectCredentialDialog
          open={!!connectProvider}
          onOpenChange={(v) => {
            if (!v) setConnectProvider(null);
          }}
          provider={connectProvider}
          onCreated={(cred) => {
            setCredentials((prev) => [cred, ...prev]);
            setConnectProvider(null);
          }}
        />
      )}
    </div>
  );
}
