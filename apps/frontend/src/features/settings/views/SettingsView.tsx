"use client";

import { useState } from "react";
import { Key, Eye, EyeOff, Save, Plus, Trash2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface ApiKeyEntry {
  id: string;
  provider: string;
  name: string;
  maskedKey: string;
  isDefault: boolean;
}

const PROVIDERS = [
  { id: "openai", label: "OpenAI", description: "GPT-4o, Embeddings" },
  { id: "anthropic", label: "Anthropic", description: "Claude Sonnet, Haiku" },
  { id: "cohere", label: "Cohere", description: "Reranking, Embeddings" },
];

export function SettingsView() {
  const [keys, setKeys] = useState<ApiKeyEntry[]>([]);
  const [addingProvider, setAddingProvider] = useState<string | null>(null);
  const [newKeyValue, setNewKeyValue] = useState("");
  const [newKeyName, setNewKeyName] = useState("");
  const [showKey, setShowKey] = useState(false);

  const handleAddKey = (provider: string) => {
    if (!newKeyValue.trim()) return;
    const entry: ApiKeyEntry = {
      id: crypto.randomUUID(),
      provider,
      name: newKeyName || `${provider} key`,
      maskedKey: newKeyValue.slice(0, 8) + "..." + newKeyValue.slice(-4),
      isDefault: keys.filter((k) => k.provider === provider).length === 0,
    };
    setKeys((prev) => [...prev, entry]);
    setAddingProvider(null);
    setNewKeyValue("");
    setNewKeyName("");
  };

  const removeKey = (id: string) => {
    setKeys((prev) => prev.filter((k) => k.id !== id));
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border px-6 py-3">
        <h1 className="text-lg font-semibold">Settings</h1>
      </div>

      <div className="flex-1 p-6">
        <div className="max-w-2xl space-y-8">
          {/* API Keys */}
          <section>
            <div className="mb-4">
              <h2 className="text-base font-semibold">API Keys</h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Manage API keys for LLM providers. Keys are encrypted at rest.
              </p>
            </div>

            <div className="space-y-4">
              {PROVIDERS.map((provider) => {
                const providerKeys = keys.filter(
                  (k) => k.provider === provider.id
                );
                const isAdding = addingProvider === provider.id;

                return (
                  <div
                    key={provider.id}
                    className="rounded-xl border border-border bg-muted/50 p-4"
                  >
                    <div className="flex items-center justify-between mb-3">
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
                      {!isAdding && (
                        <Button
                          onClick={() => setAddingProvider(provider.id)}
                          variant="outline"
                          size="sm"
                          className="gap-1 border-border bg-muted text-xs"
                        >
                          <Plus className="h-3 w-3" />
                          Add Key
                        </Button>
                      )}
                    </div>

                    {/* Existing keys */}
                    {providerKeys.length > 0 && (
                      <div className="space-y-1.5 mb-3">
                        {providerKeys.map((k) => (
                          <div
                            key={k.id}
                            className="flex items-center gap-3 rounded-lg bg-muted px-3 py-2"
                          >
                            <span className="text-xs font-medium flex-1">
                              {k.name}
                            </span>
                            <code className="text-[10px] text-muted-foreground font-mono">
                              {k.maskedKey}
                            </code>
                            {k.isDefault && (
                              <Badge className="text-[9px] h-4 px-1 bg-emerald-500/15 text-emerald-400 border-emerald-500/20">
                                Default
                              </Badge>
                            )}
                            <button
                              onClick={() => removeKey(k.id)}
                              className="text-muted-foreground hover:text-red-400 transition-colors"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Add key form */}
                    {isAdding && (
                      <div className="space-y-2 rounded-lg border border-border bg-muted/50 p-3 mt-2">
                        <Input
                          value={newKeyName}
                          onChange={(e) => setNewKeyName(e.target.value)}
                          placeholder="Key name (optional)"
                          className="h-7 bg-muted border-border text-xs"
                        />
                        <div className="relative">
                          <Input
                            value={newKeyValue}
                            onChange={(e) => setNewKeyValue(e.target.value)}
                            type={showKey ? "text" : "password"}
                            placeholder="sk-..."
                            className="h-7 bg-muted border-border text-xs font-mono pr-8"
                          />
                          <button
                            type="button"
                            onClick={() => setShowKey(!showKey)}
                            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground/70"
                          >
                            {showKey ? (
                              <EyeOff className="h-3 w-3" />
                            ) : (
                              <Eye className="h-3 w-3" />
                            )}
                          </button>
                        </div>
                        <div className="flex justify-end gap-2">
                          <Button
                            onClick={() => {
                              setAddingProvider(null);
                              setNewKeyValue("");
                              setNewKeyName("");
                            }}
                            variant="ghost"
                            size="sm"
                            className="text-xs h-7"
                          >
                            Cancel
                          </Button>
                          <Button
                            onClick={() => handleAddKey(provider.id)}
                            disabled={!newKeyValue.trim()}
                            size="sm"
                            className="gap-1 text-xs h-7 bg-primary text-primary-foreground hover:bg-primary/90"
                          >
                            <Save className="h-3 w-3" />
                            Save
                          </Button>
                        </div>
                      </div>
                    )}

                    {providerKeys.length === 0 && !isAdding && (
                      <p className="text-[11px] text-muted-foreground">No keys configured</p>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* General settings */}
          <section>
            <div className="mb-4">
              <h2 className="text-base font-semibold">General</h2>
            </div>
            <div className="rounded-xl border border-border bg-muted/50 p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Default LLM Provider</p>
                  <p className="text-[11px] text-muted-foreground">Used when creating new agents</p>
                </div>
                <select className="rounded-lg border border-border bg-muted px-3 py-1.5 text-xs text-foreground/70">
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>
              <div className="h-px bg-border" />
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Default Model</p>
                  <p className="text-[11px] text-muted-foreground">Pre-selected model for new agents</p>
                </div>
                <select className="rounded-lg border border-border bg-muted px-3 py-1.5 text-xs text-foreground/70">
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="gpt-4o-mini">GPT-4o Mini</option>
                  <option value="claude-sonnet-4-20250514">Claude Sonnet 4</option>
                </select>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
