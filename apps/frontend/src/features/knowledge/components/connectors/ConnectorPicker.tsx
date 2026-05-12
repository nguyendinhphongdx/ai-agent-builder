"use client";

import {
  Cloud,
  FileText,
  FolderOpen,
  Globe,
  Plug,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  CONNECTOR_PROVIDERS,
  type ConnectorProvider,
} from "../../data/connectorProviders";

const ICONS: Record<string, React.ElementType> = {
  Cloud,
  FileText,
  FolderOpen,
  Globe,
};

const AUTH_LABEL: Record<ConnectorProvider["authStyle"], string> = {
  none: "No auth",
  "api-key": "API key",
  "oauth-token": "Token",
  "sa-json": "Service account",
  "app-only": "Azure AD app",
};

const AUTH_TONE: Record<ConnectorProvider["authStyle"], string> = {
  none: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  "api-key": "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  "oauth-token": "bg-sky-500/15 text-sky-700 dark:text-sky-300",
  "sa-json": "bg-violet-500/15 text-violet-700 dark:text-violet-300",
  "app-only": "bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-300",
};

/**
 * Provider gallery — click a card → ``ConnectorForm`` for that
 * provider. Stays a pure component (no fetching) so the parent
 * controls the picker → form transition.
 */
export function ConnectorPicker({
  onSelect,
}: {
  onSelect: (provider: ConnectorProvider) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-base font-semibold">Connect a data source</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Index files / pages from one of the providers below. Each tick the
          scheduler picks up newly changed items and adds them to this
          knowledge base.
        </p>
      </div>

      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {CONNECTOR_PROVIDERS.map((p) => {
          const Icon = ICONS[p.icon] ?? Plug;
          return (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => onSelect(p)}
                className={cn(
                  "group flex w-full flex-col items-start gap-2 rounded-xl border border-border bg-card p-4 text-left transition-colors",
                  "hover:border-primary/40 hover:bg-accent/40",
                )}
              >
                <div className="flex w-full items-center justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                      AUTH_TONE[p.authStyle],
                    )}
                  >
                    {AUTH_LABEL[p.authStyle]}
                  </span>
                </div>
                <div>
                  <div className="text-sm font-semibold">{p.label}</div>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {p.description}
                  </p>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
