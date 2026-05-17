"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  Plug,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  systemPaymentProvidersService,
  type SystemPaymentProviderGuide,
  type SystemPaymentProviderRow,
} from "@/lib/api/systemPaymentProvidersService";

/**
 * Platform admin surface for ``payment_provider_configs``.
 *
 * Layout: provider list on the left, edit form on the right. Secrets
 * never leave the server in plaintext — the form shows masked previews
 * and only sends a ``secrets`` field when the operator actually types
 * a new value (sending ``null`` preserves the existing blob).
 *
 * Editable scope: secrets, non-secret config knobs, enabled flag, test-
 * vs live-mode toggle. Adding a *new* provider code from this UI isn't
 * supported — provider classes live in code and seed their row on first
 * boot; this page just toggles + fills the secrets.
 */
export function PaymentProvidersView() {
  const q = useQuery({
    queryKey: ["system", "payment-providers"],
    queryFn: () => systemPaymentProvidersService.list(),
    staleTime: 15_000,
  });

  const [selected, setSelected] = useState<string | null>(null);
  const rows = q.data ?? [];
  const current = rows.find((r) => r.code === selected) ?? rows[0] ?? null;

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <header>
        <h1 className="text-xl font-bold tracking-tight">Payment providers</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Stripe / MoMo / future gateways. Secrets are encrypted at rest;
          flipping <code className="rounded bg-muted px-1 font-mono text-[10px]">is_enabled</code>{" "}
          gates the public checkout endpoint.
        </p>
      </header>

      {q.isLoading ? (
        <div className="mt-12 flex items-center justify-center">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : rows.length === 0 ? (
        <p className="mt-12 text-center text-xs text-muted-foreground">
          No providers available. Provider classes are registered in code —
          add a class under{" "}
          <code className="rounded bg-muted px-1 font-mono text-[10px]">
            commerce/payments/checkout/providers/
          </code>{" "}
          to enable it here.
        </p>
      ) : (
        <div className="mt-6 grid grid-cols-[260px_1fr] gap-6">
          <ProviderList
            rows={rows}
            selected={current?.code ?? null}
            onSelect={setSelected}
          />
          {current ? (
            <ProviderEditor key={current.code} row={current} />
          ) : null}
        </div>
      )}
    </div>
  );
}

/* ─── List ──────────────────────────────────────────────────────── */

function ProviderList({
  rows,
  selected,
  onSelect,
}: {
  rows: SystemPaymentProviderRow[];
  selected: string | null;
  onSelect: (code: string) => void;
}) {
  return (
    <ul className="space-y-1">
      {rows.map((r) => {
        const active = r.code === selected;
        return (
          <li key={r.code}>
            <button
              type="button"
              onClick={() => onSelect(r.code)}
              className={cn(
                "flex w-full items-start gap-3 rounded-md border px-3 py-2.5 text-left transition-colors",
                active
                  ? "border-primary/40 bg-accent"
                  : "border-border hover:bg-accent/50",
              )}
            >
              <Plug className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">
                    {r.display_name}
                  </span>
                  {!r.persisted ? (
                    <Badge variant="outline" className="h-4 px-1.5 text-[9px]">
                      not configured
                    </Badge>
                  ) : r.is_enabled ? (
                    <Badge variant="default" className="h-4 px-1.5 text-[9px]">
                      live
                    </Badge>
                  ) : (
                    <Badge variant="secondary" className="h-4 px-1.5 text-[9px]">
                      off
                    </Badge>
                  )}
                </div>
                <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                  {r.code}
                  {r.persisted ? (r.is_test_mode ? " · test" : " · prod") : ""}
                </p>
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

/* ─── Editor ────────────────────────────────────────────────────── */

function ProviderEditor({ row }: { row: SystemPaymentProviderRow }) {
  const qc = useQueryClient();
  const [displayName, setDisplayName] = useState(row.display_name);
  const [isEnabled, setIsEnabled] = useState(row.is_enabled);
  const [isTestMode, setIsTestMode] = useState(row.is_test_mode);
  // Secrets the user has actually typed in this session. Keys absent
  // from this map → preserve server-side. Send `{}` to wipe all.
  const [secretEdits, setSecretEdits] = useState<Record<string, string>>({});
  const [configValues, setConfigValues] = useState<Record<string, string>>(
    () => mergeConfig(row),
  );
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(
    row.last_test_result
      ? { ok: row.last_test_result === "ok", message: row.last_test_result }
      : null,
  );

  const save = useMutation({
    mutationFn: () =>
      systemPaymentProvidersService.upsert(row.code, {
        display_name: displayName,
        kind: row.kind,
        is_enabled: isEnabled,
        is_test_mode: isTestMode,
        secrets: Object.keys(secretEdits).length > 0 ? secretEdits : null,
        config: collectConfig(configValues),
      }),
    onSuccess: () => {
      setSecretEdits({});
      qc.invalidateQueries({ queryKey: ["system", "payment-providers"] });
    },
  });

  const test = useMutation({
    mutationFn: () => systemPaymentProvidersService.test(row.code),
    onSuccess: (r) => {
      setTestResult(r);
      qc.invalidateQueries({ queryKey: ["system", "payment-providers"] });
    },
  });

  return (
    <div className="space-y-6 rounded-lg border border-border bg-background p-6">
      {!row.persisted && (
        <div className="-mx-2 rounded-md border border-dashed border-border bg-muted/30 px-4 py-3 text-xs text-muted-foreground">
          <strong className="font-semibold text-foreground">Not configured yet.</strong>{" "}
          Fill in the secrets + config below and hit Save to create the
          database row. The provider stays disabled until you flip{" "}
          <code className="rounded bg-background px-1 font-mono text-[10px]">is_enabled</code>.
        </div>
      )}

      {row.guide && (
        <SetupGuide
          guide={row.guide}
          /* Default to expanded on a fresh, unsaved row so first-time
           * operators see the instructions without an extra click. */
          defaultOpen={!row.persisted}
        />
      )}
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2 flex-1">
          <Label htmlFor="display-name" className="text-[11px] uppercase tracking-wider text-muted-foreground">
            Display name
          </Label>
          <Input
            id="display-name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="h-9 text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-3 pt-6">
          <ToggleRow
            id="enabled"
            label="Enabled"
            value={isEnabled}
            onChange={setIsEnabled}
          />
          <ToggleRow
            id="testmode"
            label="Test mode"
            value={isTestMode}
            onChange={setIsTestMode}
          />
        </div>
      </div>

      {row.secret_keys.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-[11px] uppercase tracking-wider text-muted-foreground">
            Secrets
          </h3>
          <div className="space-y-3 rounded-md border border-border bg-muted/20 p-4">
            {row.secret_keys.map((k) => {
              const typed = secretEdits[k.key];
              const preview = row.secrets_preview[k.key] ?? "";
              return (
                <div key={k.key} className="grid grid-cols-[180px_1fr] items-start gap-3">
                  <Label className="pt-1.5 text-xs text-foreground" htmlFor={`secret-${k.key}`}>
                    {k.label}
                    {k.is_set && typed === undefined && (
                      <span className="ml-2 text-[10px] text-muted-foreground">
                        ({preview || "set"})
                      </span>
                    )}
                  </Label>
                  <div className="space-y-1">
                    <Input
                      id={`secret-${k.key}`}
                      type="password"
                      value={typed ?? ""}
                      placeholder={k.is_set ? "•••• keep existing" : "Enter secret"}
                      onChange={(e) =>
                        setSecretEdits((prev) => ({ ...prev, [k.key]: e.target.value }))
                      }
                      className="h-8 font-mono text-xs"
                    />
                    {k.hint && (
                      <p className="text-[10px] leading-relaxed text-muted-foreground">
                        {k.hint}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-muted-foreground">
            Empty fields are preserved on save. To wipe a key, type the new value
            or contact ops to clear the row directly.
          </p>
        </section>
      )}

      {row.config_keys.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-[11px] uppercase tracking-wider text-muted-foreground">
            Configuration
          </h3>
          <div className="space-y-3 rounded-md border border-border bg-muted/20 p-4">
            {row.config_keys.map((k) => (
              <div key={k.key} className="grid grid-cols-[180px_1fr] items-start gap-3">
                <Label className="pt-1.5 text-xs text-foreground" htmlFor={`cfg-${k.key}`}>
                  {k.label}
                </Label>
                <div className="space-y-1">
                  <Input
                    id={`cfg-${k.key}`}
                    value={configValues[k.key] ?? ""}
                    onChange={(e) =>
                      setConfigValues((prev) => ({ ...prev, [k.key]: e.target.value }))
                    }
                    className="h-8 text-xs"
                  />
                  {k.hint && (
                    <p className="text-[10px] leading-relaxed text-muted-foreground">
                      {k.hint}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            disabled={test.isPending}
            onClick={() => test.mutate()}
          >
            {test.isPending ? (
              <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
            ) : null}
            Test connection
          </Button>
          {testResult ? (
            <span
              className={cn(
                "flex items-center gap-1.5 text-xs",
                testResult.ok ? "text-emerald-600 dark:text-emerald-400" : "text-destructive",
              )}
            >
              {testResult.ok ? (
                <CheckCircle2 className="h-3.5 w-3.5" />
              ) : (
                <XCircle className="h-3.5 w-3.5" />
              )}
              {testResult.message}
            </span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {save.isError && (
            <span className="text-xs text-destructive">Save failed</span>
          )}
          {save.isSuccess && (
            <span className="text-xs text-emerald-600 dark:text-emerald-400">Saved</span>
          )}
          <Button
            size="sm"
            disabled={save.isPending}
            onClick={() => save.mutate()}
          >
            {save.isPending ? (
              <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />
            ) : null}
            Save changes
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ─── Setup guide ───────────────────────────────────────────────── */

function SetupGuide({
  guide,
  defaultOpen,
}: {
  guide: SystemPaymentProviderGuide;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const docs = (guide.docs ?? []) as [string, string][];
  return (
    <section className="rounded-md border border-border bg-muted/20">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-4 py-2.5 text-left transition-colors hover:bg-accent/30"
      >
        <BookOpen className="h-3.5 w-3.5 text-primary" />
        <span className="text-xs font-medium text-foreground">Setup guide</span>
        <span className="ml-auto">
          {open ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </span>
      </button>
      {open && (
        <div className="space-y-4 border-t border-border px-4 py-4 text-xs leading-relaxed text-foreground/90">
          <p className="text-muted-foreground">{guide.intro}</p>

          {guide.webhook_path && (
            <div className="rounded-md border border-border bg-background px-3 py-2">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                Webhook URL to register with the provider
              </p>
              <code className="mt-1 block break-all font-mono text-[11px] text-foreground">
                {"<your-api-base>"}
                {guide.webhook_path}
              </code>
            </div>
          )}

          <ol className="list-decimal space-y-2 pl-5 marker:text-muted-foreground">
            {guide.steps.map((step, i) => (
              <li key={i} className="text-foreground/90">
                {step}
              </li>
            ))}
          </ol>

          {docs.length > 0 && (
            <div className="border-t border-border pt-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
                Reference docs
              </p>
              <ul className="mt-1.5 space-y-1">
                {docs.map(([label, url]) => (
                  <li key={url}>
                    <a
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                    >
                      {label}
                      <ExternalLink className="h-2.5 w-2.5" />
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function ToggleRow({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted/20 px-3 py-2">
      <Label htmlFor={id} className="text-xs text-foreground">
        {label}
      </Label>
      <Switch id={id} checked={value} onCheckedChange={onChange} />
    </div>
  );
}

function mergeConfig(row: SystemPaymentProviderRow): Record<string, string> {
  const out: Record<string, string> = {};
  for (const k of row.config_keys) {
    const v = row.config[k.key];
    out[k.key] = v == null ? "" : String(v);
  }
  return out;
}

function collectConfig(values: Record<string, string>): Record<string, unknown> {
  // Drop blank entries so the JSONB column stays compact. Numeric-looking
  // values stay strings — the backend coerces as needed.
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(values)) {
    const trimmed = v.trim();
    if (trimmed === "") continue;
    out[k] = trimmed;
  }
  return out;
}
