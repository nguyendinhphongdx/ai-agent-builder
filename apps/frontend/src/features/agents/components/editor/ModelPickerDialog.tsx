"use client";

import { useMemo, useState, useEffect } from "react";
import {
  Search,
  Check,
  Bot,
  Sparkles,
  Eye,
  Wrench,
  Brain,
  Braces,
  Lock,
  Plus,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  useModelCatalog,
  findModel,
  findProvider,
  type ModelCapability,
  type ModelCatalogEntry,
} from "@/lib/models/catalog";
import type { AICredentialResponse } from "@/lib/api/aiCredentialService";
import { ConnectCredentialDialog } from "./ConnectCredentialDialog";

/* ─── Helpers ─────────────────────────────────────────────────────── */

const CAPABILITY_META: Record<
  ModelCapability,
  { label: string; icon: typeof Wrench }
> = {
  tools: { label: "Tools", icon: Wrench },
  vision: { label: "Vision", icon: Eye },
  json_mode: { label: "JSON mode", icon: Braces },
  thinking: { label: "Thinking", icon: Brain },
};

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return `${n}`;
}

/* ─── Props ───────────────────────────────────────────────────────── */

interface ModelPickerDialogProps {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  value: string;                                    // current model_id
  credentialId: string | null;
  credentials: AICredentialResponse[];
  onSelect: (modelId: string, credentialId: string) => void;
  onCredentialCreated: (cred: AICredentialResponse) => void;
}

/* ─── Component ───────────────────────────────────────────────────── */

export function ModelPickerDialog(props: ModelPickerDialogProps) {
  // Render body only when open — local state resets naturally via remount.
  // Avoids the "reset-on-open" effect that would otherwise set state inside useEffect.
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      {props.open && <PickerBody {...props} />}
    </Dialog>
  );
}

function PickerBody({
  onOpenChange,
  value,
  credentialId,
  credentials,
  onSelect,
  onCredentialCreated,
}: ModelPickerDialogProps) {
  const { data: catalog } = useModelCatalog();
  const models = useMemo(() => catalog?.models ?? [], [catalog]);
  const providers = useMemo(() => catalog?.providers ?? [], [catalog]);

  const [search, setSearch] = useState("");
  // Inverted semantic: track *excluded* providers so we don't need to seed
  // state from catalog data (empty set = all providers active).
  const [excludedProviders, setExcludedProviders] = useState<Set<string>>(new Set());
  const [enabledCaps, setEnabledCaps] = useState<Set<ModelCapability>>(new Set());

  const activeProviders = useMemo(
    () => new Set(providers.map((p) => p.id).filter((id) => !excludedProviders.has(id))),
    [providers, excludedProviders],
  );

  const [selectedModelId, setSelectedModelId] = useState<string>(value);
  const [selectedCredentialId, setSelectedCredentialId] = useState<string | null>(
    credentialId,
  );
  const [connectProvider, setConnectProvider] = useState<string | null>(null);

  // Credentials grouped by provider, for O(1) lookup
  const credentialsByProvider = useMemo(() => {
    const map = new Map<string, AICredentialResponse[]>();
    for (const c of credentials) {
      const list = map.get(c.provider) ?? [];
      list.push(c);
      map.set(c.provider, list);
    }
    return map;
  }, [credentials]);

  // Filter models by search + provider + capabilities
  const filteredModels = useMemo(() => {
    return models.filter((m) => {
      if (!activeProviders.has(m.provider)) return false;
      if (enabledCaps.size > 0) {
        for (const cap of enabledCaps) {
          if (!m.capabilities.includes(cap)) return false;
        }
      }
      if (search.trim()) {
        const q = search.toLowerCase();
        if (
          !m.name.toLowerCase().includes(q) &&
          !m.model.toLowerCase().includes(q) &&
          !findProvider(providers, m.provider)?.label.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      return true;
    });
  }, [models, providers, search, activeProviders, enabledCaps]);

  const selectedModel = findModel(models, selectedModelId);
  const availableCredsForSelected = selectedModel
    ? credentialsByProvider.get(selectedModel.provider) ?? []
    : [];
  const selectedModelHasCredential = availableCredsForSelected.length > 0;

  // Derive effective credential id instead of syncing via effect — eliminates
  // the need to setState when the selected model's provider changes.
  const effectiveCredentialId: string | null = useMemo(() => {
    if (!selectedModelHasCredential) return null;
    if (
      selectedCredentialId &&
      availableCredsForSelected.some((c) => c.id === selectedCredentialId)
    ) {
      return selectedCredentialId;
    }
    return availableCredsForSelected[0]?.id ?? null;
  }, [selectedCredentialId, selectedModelHasCredential, availableCredsForSelected]);

  const toggleProvider = (id: string) => {
    setExcludedProviders((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleCapability = (cap: ModelCapability) => {
    setEnabledCaps((prev) => {
      const next = new Set(prev);
      if (next.has(cap)) next.delete(cap);
      else next.add(cap);
      return next;
    });
  };

  const resetFilters = () => {
    setExcludedProviders(new Set());
    setEnabledCaps(new Set());
    setSearch("");
  };

  const filterCount =
    (providers.length - activeProviders.size) + enabledCaps.size + (search ? 1 : 0);

  const handleSelect = () => {
    if (!selectedModel || !selectedCredentialId) return;
    onSelect(selectedModel.id, selectedCredentialId);
    onOpenChange(false);
  };

  const handleConnect = (provider: string) => setConnectProvider(provider);

  return (
    <>
      <DialogContent
        className="flex h-[85vh] max-h-[800px] w-[95vw] max-w-[1200px] flex-col gap-0 p-0 sm:max-w-[1200px]"
        showCloseButton={false}
      >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border px-5 py-3">
            <div>
              <DialogTitle>Select your Agent&apos;s AI Model</DialogTitle>
              <DialogDescription className="mt-0.5 text-xs">
                Chọn model và credential sẽ được dùng để chạy agent.
              </DialogDescription>
            </div>
          </div>

          {/* Body: filters | list | detail */}
          <div className="grid flex-1 min-h-0 grid-cols-[220px_1fr_320px]">
            {/* ── Left: Filters ─────────────────────────────────── */}
            <div className="flex flex-col overflow-y-auto border-r border-border p-4">
              <div className="mb-3 flex items-center justify-between">
                <h4 className="text-xs font-semibold">Filters</h4>
                {filterCount > 0 && (
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="text-[10px] text-muted-foreground hover:text-foreground"
                  >
                    Reset ({filterCount})
                  </button>
                )}
              </div>

              {/* Providers */}
              <div className="mb-5">
                <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">
                  Provider
                </p>
                <div className="space-y-1">
                  {providers.map((p) => {
                    const hasCred = (credentialsByProvider.get(p.id) ?? []).length > 0;
                    const checked = activeProviders.has(p.id);
                    return (
                      <label
                        key={p.id}
                        className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-colors hover:bg-accent/50"
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() => toggleProvider(p.id)}
                          className="h-3.5 w-3.5 rounded border-border"
                        />
                        <span className="flex-1">{p.label}</span>
                        {!hasCred && (
                          <Lock className="h-3 w-3 text-muted-foreground/60" />
                        )}
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Capabilities */}
              <div>
                <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">
                  Capabilities
                </p>
                <div className="space-y-1">
                  {(Object.entries(CAPABILITY_META) as [
                    ModelCapability,
                    (typeof CAPABILITY_META)[ModelCapability],
                  ][]).map(([cap, meta]) => {
                    const Icon = meta.icon;
                    return (
                      <label
                        key={cap}
                        className="flex cursor-pointer items-center gap-2 rounded-md px-1.5 py-1 text-xs transition-colors hover:bg-accent/50"
                      >
                        <input
                          type="checkbox"
                          checked={enabledCaps.has(cap)}
                          onChange={() => toggleCapability(cap)}
                          className="h-3.5 w-3.5 rounded border-border"
                        />
                        <Icon className="h-3 w-3 text-muted-foreground" />
                        <span>{meta.label}</span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* ── Middle: Search + list ───────────────────────── */}
            <div className="flex min-h-0 flex-col">
              <div className="border-b border-border px-4 py-2.5">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search models…"
                    className="h-8 pl-7 text-xs"
                  />
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-2">
                {filteredModels.length === 0 ? (
                  <div className="flex h-full items-center justify-center p-6 text-center">
                    <p className="text-xs text-muted-foreground">
                      Không có model phù hợp. Thử bỏ bớt bộ lọc.
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-1">
                    {filteredModels.map((m) => {
                      const hasCred =
                        (credentialsByProvider.get(m.provider) ?? []).length > 0;
                      const isSelected = m.id === selectedModelId;
                      return (
                        <ModelRow
                          key={m.id}
                          model={m}
                          providerLabel={findProvider(providers, m.provider)?.label ?? m.provider}
                          hasCred={hasCred}
                          isSelected={isSelected}
                          onClick={() => setSelectedModelId(m.id)}
                        />
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* ── Right: Detail ───────────────────────────────── */}
            <div className="flex min-h-0 flex-col border-l border-border">
              {selectedModel ? (
                <div className="flex-1 overflow-y-auto p-4">
                  <div className="flex items-start gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-muted">
                      <Sparkles className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">
                        {selectedModel.name}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {findProvider(providers, selectedModel.provider)?.label}
                      </p>
                    </div>
                  </div>

                  <p className="mt-3 text-xs text-muted-foreground">
                    {selectedModel.description}
                  </p>

                  <Separator className="my-4" />

                  <dl className="space-y-2 text-xs">
                    <SpecRow label="Context window" value={`${formatTokens(selectedModel.context_window)} tokens`} />
                    <SpecRow label="Output limit" value={`${formatTokens(selectedModel.max_output)} tokens`} />
                    {selectedModel.capabilities.length > 0 && (
                      <div>
                        <dt className="mb-1 text-[11px] text-muted-foreground">
                          Capabilities
                        </dt>
                        <dd className="flex flex-wrap gap-1">
                          {selectedModel.capabilities.map((cap) => {
                            const meta = CAPABILITY_META[cap];
                            const Icon = meta.icon;
                            return (
                              <Badge
                                key={cap}
                                variant="secondary"
                                className="gap-1 px-1.5 py-0 text-[10px]"
                              >
                                <Icon className="h-2.5 w-2.5" />
                                {meta.label}
                              </Badge>
                            );
                          })}
                        </dd>
                      </div>
                    )}
                  </dl>

                  <Separator className="my-4" />

                  {/* Credential picker */}
                  <div className="space-y-1.5">
                    <p className="text-[11px] font-medium text-muted-foreground">
                      Credential
                    </p>
                    {selectedModelHasCredential ? (
                      <Select
                        value={selectedCredentialId ?? undefined}
                        onValueChange={setSelectedCredentialId}
                      >
                        <SelectTrigger className="h-9 w-full text-xs">
                          <SelectValue placeholder="Select credential" />
                        </SelectTrigger>
                        <SelectContent>
                          {availableCredsForSelected.map((c) => (
                            <SelectItem key={c.id} value={c.id} className="text-xs">
                              <span className="truncate">{c.name}</span>
                              <span className="ml-2 font-mono text-[10px] text-muted-foreground">
                                {c.masked_key}
                              </span>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <div className="rounded-md border border-dashed border-border bg-muted/30 p-3 text-center">
                        <Lock className="mx-auto mb-1.5 h-3.5 w-3.5 text-muted-foreground" />
                        <p className="mb-2 text-[11px] text-muted-foreground">
                          Chưa có credential cho {findProvider(providers, selectedModel.provider)?.label}.
                        </p>
                      </div>
                    )}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-8 w-full gap-1.5 text-xs"
                      onClick={() => handleConnect(selectedModel.provider)}
                    >
                      <Plus className="h-3 w-3" />
                      Connect {findProvider(providers, selectedModel.provider)?.label}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex h-full items-center justify-center p-6 text-center">
                  <p className="text-xs text-muted-foreground">Chọn một model để xem chi tiết.</p>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2 border-t border-border bg-muted/30 px-5 py-3">
            <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!selectedModel || !selectedCredentialId}
              onClick={handleSelect}
            >
              Select Model
            </Button>
        </div>
      </DialogContent>

      {/* Sub-dialog for creating a credential */}
      {connectProvider && (
        <ConnectCredentialDialog
          open={!!connectProvider}
          onOpenChange={(v) => {
            if (!v) setConnectProvider(null);
          }}
          provider={connectProvider}
          onCreated={(cred) => {
            onCredentialCreated(cred);
            // Auto-select the new credential if it matches current model's provider
            if (selectedModel && cred.provider === selectedModel.provider) {
              setSelectedCredentialId(cred.id);
            }
            setConnectProvider(null);
          }}
        />
      )}
    </>
  );
}

/* ─── ModelRow ───────────────────────────────────────────────────── */

interface ModelRowProps {
  model: ModelCatalogEntry;
  providerLabel: string;
  hasCred: boolean;
  isSelected: boolean;
  onClick: () => void;
}

function ModelRow({ model, providerLabel, hasCred, isSelected, onClick }: ModelRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex items-center gap-3 rounded-lg border border-transparent px-3 py-2.5 text-left transition-colors",
        isSelected
          ? "border-primary/30 bg-primary/5"
          : "hover:border-border hover:bg-accent/40",
        !hasCred && "opacity-60",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border",
          hasCred ? "bg-muted" : "bg-muted/40",
        )}
      >
        {hasCred ? (
          <Bot className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Lock className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium">{model.name}</p>
          {!hasCred && (
            <Badge variant="outline" className="shrink-0 px-1 py-0 text-[9px]">
              Not connected
            </Badge>
          )}
        </div>
        <p className="truncate text-[11px] text-muted-foreground">
          {providerLabel}
        </p>
      </div>

      <div className="flex shrink-0 flex-col items-end gap-0.5 text-[10px] text-muted-foreground">
        <span>{formatTokens(model.context_window)} tokens</span>
        <span>out {formatTokens(model.max_output)}</span>
      </div>

      {isSelected && <Check className="ml-1 h-4 w-4 shrink-0 text-primary" />}
    </button>
  );
}

/* ─── SpecRow ────────────────────────────────────────────────────── */

function SpecRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-[11px] text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </div>
  );
}
