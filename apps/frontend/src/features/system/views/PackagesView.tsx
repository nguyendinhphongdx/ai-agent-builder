"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, Loader2, Minus, X } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  systemPackagesService,
  type SystemPackageRow,
} from "@/lib/api/systemPackagesService";

/** Plan-comparison matrix. Rows = features, cols = plans.
 *
 *  Read-only by design — plans are declared in ``plans.py`` and changes
 *  are a code deploy, not an admin form. Active-org counts come from
 *  live DB state so this also doubles as a "who's on what" snapshot.
 */
export function PackagesView() {
  const q = useQuery({
    queryKey: ["system", "packages"],
    queryFn: () => systemPackagesService.list(),
    staleTime: 60_000,
  });

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <header>
        <h1 className="text-xl font-bold tracking-tight">Packages</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Plan catalogue + active org counts. Edit{" "}
          <code className="rounded bg-muted px-1 font-mono text-[10px]">
            commerce/payments/subscriptions/plans.py
          </code>{" "}
          and redeploy to change a tier.
        </p>
      </header>

      <div className="mt-6 overflow-hidden rounded-lg border border-border">
        {q.isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Matrix plans={q.data ?? []} />
        )}
      </div>
    </div>
  );
}

/* ─── Matrix ─────────────────────────────────────────────────── */

// Feature rows we want to surface, in display order. Anything in the
// per-plan ``features`` dict that we don't list here still works at
// the server — we just don't render a row for it.
const FEATURE_ROWS: { key: string; label: string }[] = [
  { key: "audit_retention_days", label: "Audit log retention" },
  { key: "custom_roles", label: "Custom roles" },
  { key: "sso", label: "SSO (SAML/OIDC)" },
  { key: "mfa_enforce", label: "MFA enforcement" },
  { key: "webhook_hmac", label: "Webhook HMAC" },
  { key: "trace_provider", label: "External tracing" },
  { key: "ip_allowlist", label: "IP allowlist" },
  { key: "scim", label: "SCIM provisioning" },
];

function Matrix({ plans }: { plans: SystemPackageRow[] }) {
  if (plans.length === 0) {
    return (
      <p className="px-4 py-16 text-center text-xs text-muted-foreground">
        No plans configured.
      </p>
    );
  }
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="bg-muted/40">
          <th className="sticky left-0 z-10 bg-muted/40 px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-muted-foreground" />
          {plans.map((p) => (
            <th key={p.code} className="px-4 py-3 text-left">
              <div className="flex items-baseline justify-between gap-2">
                <span className="text-sm font-bold text-foreground">{p.name}</span>
                <span className="rounded bg-background px-1.5 py-0.5 text-[10px] tabular-nums text-muted-foreground">
                  {p.active_orgs} org{p.active_orgs === 1 ? "" : "s"}
                </span>
              </div>
              <p className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                {p.code}
                {!p.is_self_serve && (
                  <span className="ml-1 rounded bg-muted px-1 py-0.5 text-[9px] uppercase tracking-wider">
                    hidden
                  </span>
                )}
              </p>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        <SectionHeader plans={plans} title="Quotas" />
        <QuotaRow label="Monthly LLM tokens" plans={plans} pick={(p) => p.monthly_llm_tokens} />
        <QuotaRow label="Monthly KB queries" plans={plans} pick={(p) => p.monthly_kb_queries} />
        <QuotaRow label="Workspaces" plans={plans} pick={(p) => p.max_workspaces} />
        <QuotaRow label="Members" plans={plans} pick={(p) => p.max_members} />

        <SectionHeader plans={plans} title="Features" />
        {FEATURE_ROWS.map((f) => (
          <FeatureRow key={f.key} label={f.label} fkey={f.key} plans={plans} />
        ))}

        <SectionHeader plans={plans} title="Billing" />
        <StringRow
          label="Stripe price (base)"
          plans={plans}
          pick={(p) => p.stripe_price_id}
        />
        <StringRow
          label="Stripe price (metered)"
          plans={plans}
          pick={(p) => p.stripe_metered_price_id}
        />
      </tbody>
    </table>
  );
}

function SectionHeader({ plans, title }: { plans: SystemPackageRow[]; title: string }) {
  return (
    <tr className="border-t-2 border-border bg-muted/20">
      <td className="sticky left-0 bg-muted/20 px-4 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </td>
      {plans.map((p) => (
        <td key={p.code} className="px-4 py-2" />
      ))}
    </tr>
  );
}

function QuotaRow({
  label,
  plans,
  pick,
}: {
  label: string;
  plans: SystemPackageRow[];
  pick: (p: SystemPackageRow) => number;
}) {
  return (
    <tr className="border-t border-border">
      <td className="sticky left-0 bg-background px-4 py-2.5 text-[11px] font-medium text-foreground">
        {label}
      </td>
      {plans.map((p) => {
        const v = pick(p);
        return (
          <td key={p.code} className="px-4 py-2.5 text-foreground/80">
            {v === 0 ? (
              <span className="font-medium text-emerald-600 dark:text-emerald-400">
                Unlimited
              </span>
            ) : (
              <span className="tabular-nums">{formatNumber(v)}</span>
            )}
          </td>
        );
      })}
    </tr>
  );
}

function FeatureRow({
  label,
  fkey,
  plans,
}: {
  label: string;
  fkey: string;
  plans: SystemPackageRow[];
}) {
  return (
    <tr className="border-t border-border">
      <td className="sticky left-0 bg-background px-4 py-2.5 text-[11px] font-medium text-foreground">
        {label}
      </td>
      {plans.map((p) => {
        const v = p.features[fkey];
        return (
          <td key={p.code} className="px-4 py-2.5">
            <FeatureCell value={v} />
          </td>
        );
      })}
    </tr>
  );
}

function FeatureCell({ value }: { value: boolean | number | undefined }) {
  if (value === undefined) {
    return <Minus className="h-3.5 w-3.5 text-muted-foreground/40" aria-label="not set" />;
  }
  if (typeof value === "number") {
    if (value === 0) {
      return <X className="h-3.5 w-3.5 text-muted-foreground" aria-label="no" />;
    }
    return (
      <span className="font-mono text-[11px] text-foreground/80">{value} days</span>
    );
  }
  return value ? (
    <Check
      className={cn("h-3.5 w-3.5", "text-emerald-500")}
      aria-label="yes"
    />
  ) : (
    <X className="h-3.5 w-3.5 text-muted-foreground" aria-label="no" />
  );
}

function StringRow({
  label,
  plans,
  pick,
}: {
  label: string;
  plans: SystemPackageRow[];
  pick: (p: SystemPackageRow) => string | null;
}) {
  return (
    <tr className="border-t border-border">
      <td className="sticky left-0 bg-background px-4 py-2.5 text-[11px] font-medium text-foreground">
        {label}
      </td>
      {plans.map((p) => {
        const v = pick(p);
        return (
          <td key={p.code} className="px-4 py-2.5">
            {v ? (
              <span className="font-mono text-[10px] text-foreground/80">{v}</span>
            ) : (
              <Minus className="h-3.5 w-3.5 text-muted-foreground/40" />
            )}
          </td>
        );
      })}
    </tr>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 === 0 ? 0 : 1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n % 1_000 === 0 ? 0 : 1)}K`;
  return String(n);
}
