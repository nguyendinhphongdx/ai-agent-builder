"use client";

import { useMemo } from "react";
import { Loader2 } from "lucide-react";
import { useOAuthConnections, useOAuthProviders } from "../hooks/useOAuthConnections";
import { ConnectButton } from "./ConnectButton";

interface OAuthConnectionPickerProps {
  provider: string;
  /** Currently-selected connection id (or empty string). */
  value: string;
  onChange: (connectionId: string) => void;
  /** Where the BE should redirect after the OAuth dance. Defaults
   *  to the current URL so the user lands back in the form they
   *  came from. */
  returnTo?: string;
  required?: boolean;
}

/**
 * Workspace's OAuth connections for one provider, surfaced as a
 * select + a "Connect new" button. Replaces the plain text input
 * that ConnectorForm would render otherwise — the form passes the
 * selected connection's UUID through unchanged.
 *
 *   ┌──────────────────────────────────┬───────────────┐
 *   │  Choose a Slack workspace…       │  Connect Slack│
 *   └──────────────────────────────────┴───────────────┘
 *     - or - "No connections yet — connect one to continue."
 */
export function OAuthConnectionPicker({
  provider,
  value,
  onChange,
  returnTo,
  required,
}: OAuthConnectionPickerProps) {
  const providersQ = useOAuthProviders();
  const connectionsQ = useOAuthConnections();

  const providerInfo = useMemo(
    () => providersQ.data?.find((p) => p.id === provider),
    [providersQ.data, provider],
  );

  const matching = useMemo(
    () => (connectionsQ.data ?? []).filter((c) => c.provider === provider),
    [connectionsQ.data, provider],
  );

  if (providersQ.isLoading || connectionsQ.isLoading) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-dashed border-border bg-background px-2 py-1.5 text-[11px] text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        Loading connections…
      </div>
    );
  }

  const label = providerInfo?.label ?? provider;
  const configured = providerInfo?.configured ?? false;

  if (!configured) {
    return (
      <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-700 dark:text-amber-300">
        <strong>{label} OAuth</strong> isn't configured on this deployment.
        Ask an admin to set the client id / secret env vars, then refresh.
      </div>
    );
  }

  if (matching.length === 0) {
    return (
      <div className="flex flex-col gap-2 rounded-md border border-dashed border-border bg-background p-3">
        <p className="text-[11px] text-muted-foreground">
          No {label} connections yet. Connect a workspace to wire this connector.
        </p>
        <div>
          <ConnectButton
            provider={provider}
            label={label}
            returnTo={returnTo}
            size="sm"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-stretch gap-2">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-xs"
      >
        <option value="">Choose a {label} workspace…</option>
        {matching.map((c) => (
          <option key={c.id} value={c.id}>
            {c.account_label || c.external_account_id || c.id.slice(0, 8)}
          </option>
        ))}
      </select>
      <ConnectButton
        provider={provider}
        label="new"
        returnTo={returnTo}
        size="sm"
        variant="ghost"
      />
    </div>
  );
}
