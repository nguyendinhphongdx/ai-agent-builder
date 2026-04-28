"use client";

import { useEffect, useState, useCallback } from "react";
import { Key, Plus, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useModelCatalog } from "@/lib/models/catalog";
import {
  aiCredentialService,
  type AICredentialResponse,
} from "@/lib/api/aiCredentialService";
import { ConnectCredentialDialog } from "@/features/agents/components/editor/ConnectCredentialDialog";
import { ApiTokensSection } from "../components/ApiTokensSection";
import { IntegrationsLinkSection } from "../components/IntegrationsLinkSection";

export function SettingsView() {
  const { data: catalog } = useModelCatalog();
  const providers = catalog?.providers ?? [];

  const [credentials, setCredentials] = useState<AICredentialResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectProvider, setConnectProvider] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const list = await aiCredentialService.list();
      setCredentials(list);
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
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold">Settings</h1>
      </div>

      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl space-y-10">
          {/* AI Credentials */}
          <section>
            <div className="mb-4">
              <h2 className="text-base font-semibold">AI Credentials</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Quản lý credential cho các LLM provider. Key được mã hoá trước khi lưu,
                không bao giờ hiển thị lại plaintext.
              </p>
            </div>

            {loading ? (
              <div className="flex items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : (
              <div className="space-y-3">
                {providers.map((provider) => {
                  const providerCreds = credentials.filter(
                    (c) => c.provider === provider.id,
                  );

                  return (
                    <div
                      key={provider.id}
                      className="rounded-xl border border-border bg-muted/30 p-4"
                    >
                      <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                            <Key className="h-4 w-4 text-muted-foreground" />
                          </div>
                          <div>
                            <p className="text-sm font-medium">{provider.label}</p>
                            <p className="text-[11px] text-muted-foreground">
                              {provider.description}
                            </p>
                          </div>
                        </div>
                        <Button
                          onClick={() => setConnectProvider(provider.id)}
                          variant="outline"
                          size="sm"
                          className="gap-1.5 text-xs"
                        >
                          <Plus className="h-3 w-3" />
                          Add Credential
                        </Button>
                      </div>

                      {providerCreds.length > 0 ? (
                        <div className="space-y-1.5">
                          {providerCreds.map((c) => (
                            <div
                              key={c.id}
                              className="flex items-center gap-3 rounded-lg bg-background/70 px-3 py-2"
                            >
                              <span className="flex-1 truncate text-xs font-medium">
                                {c.name}
                              </span>
                              <code className="font-mono text-[10px] text-muted-foreground">
                                {c.masked_key}
                              </code>
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
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-[11px] text-muted-foreground">
                          Chưa có credential cho {provider.label}.
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* API Tokens — for external clients calling /api/external/* */}
          <ApiTokensSection />

          {/* Integrations — channels that consume the API */}
          <IntegrationsLinkSection />
        </div>
      </div>

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
