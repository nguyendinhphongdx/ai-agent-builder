"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  CONNECTOR_PROVIDERS,
  type ConnectorField,
  type ConnectorProvider,
} from "../../data/connectorProviders";
import { kbConnectorsService } from "@/lib/api/kbConnectorsService";
import { OAuthConnectionPicker } from "@/features/connections";

interface ConnectorFormProps {
  kbId: string;
  provider: ConnectorProvider;
  onBack: () => void;
  onCreated: () => void;
}

/**
 * Render a provider-specific create form from
 * ``provider.configFields`` + ``provider.credentialFields``.
 * One generic form for ten providers — every new connector that
 * declares its schema in connectorProviders.ts gets a working
 * UI without touching this file.
 */
export function ConnectorForm({
  kbId,
  provider,
  onBack,
  onCreated,
}: ConnectorFormProps) {
  const qc = useQueryClient();
  const [name, setName] = useState(`My ${provider.label}`);
  const [config, setConfig] = useState<Record<string, unknown>>(() =>
    initialValues(provider.configFields),
  );
  const [credentials, setCredentials] = useState<Record<string, unknown>>(() =>
    initialValues(provider.credentialFields),
  );
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      kbConnectorsService.create(kbId, {
        connector_type: provider.id,
        name: name.trim() || provider.label,
        config: normaliseConfig(provider, config),
        credentials:
          provider.credentialFields.length > 0
            ? omitEmpty(credentials)
            : null,
        is_active: true,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["kb-connectors", kbId] });
      onCreated();
    },
    onError: (e: { response?: { data?: { detail?: string } }; message?: string }) => {
      setError(
        e?.response?.data?.detail ||
          e?.message ||
          "Failed to create connector",
      );
    },
  });

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <button
        type="button"
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[11px] text-muted-foreground hover:text-foreground"
      >
        <ChevronLeft className="h-3 w-3" /> Back to providers
      </button>

      <header>
        <h2 className="text-base font-semibold">Connect {provider.label}</h2>
        <p className="mt-1 text-xs text-muted-foreground">{provider.description}</p>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setError(null);
          create.mutate();
        }}
        className="space-y-5"
      >
        <FieldGroup title="General">
          <Field
            field={{ key: "name", label: "Display name", type: "text", required: true }}
            value={name}
            onChange={(v) => setName(String(v))}
          />
        </FieldGroup>

        {provider.configFields.length > 0 && (
          <FieldGroup title="Source">
            {provider.configFields.map((f) => (
              <Field
                key={f.key}
                field={f}
                value={config[f.key]}
                onChange={(v) => setConfig((c) => ({ ...c, [f.key]: v }))}
              />
            ))}
          </FieldGroup>
        )}

        {provider.credentialFields.length > 0 && (
          <FieldGroup
            title="Credentials"
            note="Stored encrypted (Fernet) on the backend. Never echoed back."
          >
            {provider.credentialFields.map((f) => (
              <Field
                key={f.key}
                field={f}
                value={credentials[f.key]}
                onChange={(v) =>
                  setCredentials((c) => ({ ...c, [f.key]: v }))
                }
              />
            ))}
          </FieldGroup>
        )}

        {error && (
          <div className="rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-300">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-2 border-t border-border pt-4">
          <Button type="button" variant="ghost" onClick={onBack}>
            Cancel
          </Button>
          <Button type="submit" disabled={create.isPending}>
            {create.isPending && <Loader2 className="mr-1.5 h-3 w-3 animate-spin" />}
            Add connector
          </Button>
        </div>
      </form>
    </div>
  );
}

function FieldGroup({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          {title}
        </h3>
        {note && <span className="text-[10px] text-muted-foreground">{note}</span>}
      </div>
      <div className="space-y-3 rounded-lg border border-border bg-card p-4">{children}</div>
    </div>
  );
}

function Field({
  field,
  value,
  onChange,
}: {
  field: ConnectorField;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  if (field.oauthPickerProvider) {
    // Dropdown of the workspace's existing OAuth connections for
    // the named provider + a Connect-new CTA. Replaces the plain
    // text input ConnectorForm would render otherwise; the form
    // still sees a plain string (the connection UUID) flow through
    // ``onChange``, so ``normaliseConfig`` keeps working unchanged.
    return (
      <FieldShell field={field}>
        <OAuthConnectionPicker
          provider={field.oauthPickerProvider}
          value={String(value ?? "")}
          onChange={onChange}
          required={field.required}
        />
      </FieldShell>
    );
  }
  if (field.type === "boolean") {
    return (
      <label className="flex items-center gap-2 text-xs">
        <input
          type="checkbox"
          checked={!!value}
          onChange={(e) => onChange(e.target.checked)}
          className="h-3.5 w-3.5 accent-primary"
        />
        <span className="font-medium">{field.label}</span>
        {field.help && (
          <span className="text-[11px] text-muted-foreground">— {field.help}</span>
        )}
      </label>
    );
  }
  if (field.type === "textarea") {
    return (
      <FieldShell field={field}>
        <textarea
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          rows={field.key.toLowerCase().includes("json") ? 8 : 4}
          className="w-full rounded-md border border-border bg-background px-2 py-1.5 font-mono text-[11px]"
          required={field.required}
        />
      </FieldShell>
    );
  }
  if (field.type === "number") {
    return (
      <FieldShell field={field}>
        <input
          type="number"
          value={Number(value ?? field.default ?? 0)}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
          required={field.required}
        />
      </FieldShell>
    );
  }
  return (
    <FieldShell field={field}>
      <input
        type={field.type === "password" ? "password" : "text"}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.placeholder}
        className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs"
        required={field.required}
        autoComplete={field.type === "password" ? "new-password" : "off"}
      />
    </FieldShell>
  );
}

function FieldShell({
  field,
  children,
}: {
  field: ConnectorField;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] font-medium">
        {field.label}
        {field.required && <span className="ml-0.5 text-rose-500">*</span>}
      </span>
      {children}
      {field.help && (
        <span className="mt-1 block text-[10px] text-muted-foreground">{field.help}</span>
      )}
    </label>
  );
}

/* ─── Helpers ──────────────────────────────────────────────── */

function initialValues(fields: ConnectorField[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of fields) {
    if (f.default !== undefined) out[f.key] = f.default;
    else if (f.type === "boolean") out[f.key] = false;
    else out[f.key] = "";
  }
  return out;
}

/** Strip empty strings (so the backend treats them as "use the
 *  default", not an explicit empty value). Coerce textarea
 *  URL/CSV lists into the array shape the Python connector
 *  expects. */
function normaliseConfig(
  provider: ConnectorProvider,
  raw: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of provider.configFields) {
    const v = raw[f.key];
    if (v === undefined || v === "") continue;

    if (f.type === "textarea" && f.key === "urls") {
      // Web crawler's URLs — split on newline / comma.
      out[f.key] = String(v)
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      continue;
    }
    out[f.key] = v;
  }
  return out;
}

function omitEmpty(raw: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(raw)) {
    if (v === undefined || v === null || v === "") continue;
    out[k] = v;
  }
  return out;
}

// Re-export so consumers can use the same picker without a separate import.
export { CONNECTOR_PROVIDERS };
