"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  Building2,
  ChevronUp,
  DollarSign,
  FileText,
  Hash,
  Loader2,
  MessageSquare,
  Search,
  ShoppingBag,
  TrendingUp,
  Users,
} from "lucide-react";
import {
  systemDashboardService,
  type SystemDashboard,
} from "@/lib/api/systemDashboardService";
import { cn } from "@/lib/utils";

/** Whole-platform snapshot — KPIs, revenue, usage, top orgs. */
export function DashboardView() {
  const q = useQuery({
    queryKey: ["system", "dashboard"],
    queryFn: () => systemDashboardService.get(),
    staleTime: 30_000,
  });

  if (q.isLoading) {
    return (
      <div className="flex h-full items-center justify-center py-16">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const d = q.data;
  if (!d) return null;

  return (
    <div className="mx-auto max-w-6xl px-8 py-8 space-y-8">
      <header className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Platform dashboard</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Updated {new Date(d.as_of).toLocaleString()}
          </p>
        </div>
        <p className="text-[10px] text-muted-foreground">
          Numbers are estimates — authoritative ledger lives in Stripe.
        </p>
      </header>

      <KpiRow d={d} />

      <div className="grid gap-5 lg:grid-cols-3">
        <PlanDistributionCard d={d} />
        <UsageCard d={d} className="lg:col-span-2" />
      </div>

      <div className="grid gap-5 lg:grid-cols-3">
        <TopOrgsCard d={d} className="lg:col-span-2" />
        <ContractsCard d={d} />
      </div>

      <RevenueBreakdownCard d={d} />
    </div>
  );
}

/* ─── KPI row ────────────────────────────────────────────────── */

function KpiRow({ d }: { d: SystemDashboard }) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      <Kpi
        icon={Building2}
        label="Organizations"
        value={d.orgs.total}
        sub={`+${d.orgs.new_30d} this month`}
      />
      <Kpi
        icon={Users}
        label="Active users (30d)"
        value={d.users.active_30d}
        sub={`${d.users.activity_rate_pct}% of ${d.users.total}`}
        tone="emerald"
      />
      <Kpi
        icon={TrendingUp}
        label="MRR (est.)"
        value={formatUSD(d.revenue.mrr_usd_cents)}
        sub={`${d.subscriptions.live} live sub${d.subscriptions.live === 1 ? "" : "s"}`}
        tone="primary"
      />
      <Kpi
        icon={ShoppingBag}
        label="Hub revenue (30d)"
        value={formatUSD(d.revenue.hub_30d_cents)}
        sub={`${d.revenue.hub_30d_purchases} purchase${d.revenue.hub_30d_purchases === 1 ? "" : "s"}`}
        tone="amber"
      />
    </div>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  tone?: "primary" | "emerald" | "amber";
}) {
  const toneClass = {
    primary: "text-primary",
    emerald: "text-emerald-500",
    amber: "text-amber-500",
  } as const;
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <Icon className={cn("h-4 w-4", tone ? toneClass[tone] : "text-foreground")} />
      </div>
      <p className="mt-2 text-2xl font-bold tabular-nums text-foreground">{value}</p>
      {sub && (
        <p className="mt-1 inline-flex items-center gap-1 text-[11px] text-muted-foreground">
          <ChevronUp className="h-3 w-3 text-emerald-500" />
          {sub}
        </p>
      )}
    </div>
  );
}

/* ─── Plan distribution (CSS conic donut) ─────────────────────── */

const PLAN_COLOR: Record<string, string> = {
  free: "#94a3b8",        // slate-400
  starter: "#0ea5e9",     // sky-500
  pro: "#10b981",         // emerald-500
  enterprise: "#8b5cf6",  // violet-500
};

function PlanDistributionCard({ d }: { d: SystemDashboard }) {
  const entries = Object.entries(d.orgs.by_plan).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, c]) => sum + c, 0);

  // Build conic-gradient string segments.
  let cumulative = 0;
  const gradStops = entries.map(([plan, count]) => {
    const startPct = total ? (cumulative / total) * 100 : 0;
    cumulative += count;
    const endPct = total ? (cumulative / total) * 100 : 0;
    return `${PLAN_COLOR[plan] ?? "#cbd5e1"} ${startPct}% ${endPct}%`;
  });
  const gradient = total
    ? `conic-gradient(${gradStops.join(", ")})`
    : "conic-gradient(#e5e7eb 0% 100%)";

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h3 className="text-sm font-semibold">Orgs by plan</h3>
      <div className="mt-4 flex items-center gap-5">
        <div
          className="relative h-28 w-28 shrink-0 rounded-full"
          style={{ background: gradient }}
        >
          <div className="absolute inset-3 flex flex-col items-center justify-center rounded-full bg-card">
            <span className="text-xl font-bold tabular-nums">{total}</span>
            <span className="text-[9px] uppercase tracking-wider text-muted-foreground">
              total
            </span>
          </div>
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          {entries.map(([plan, count]) => (
            <div key={plan} className="flex items-center gap-2 text-[11px]">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ background: PLAN_COLOR[plan] ?? "#cbd5e1" }}
              />
              <span className="font-medium capitalize text-foreground">{plan}</span>
              <span className="ml-auto tabular-nums text-muted-foreground">
                {count} · {total ? Math.round((count / total) * 100) : 0}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Usage 30d ──────────────────────────────────────────────── */

function UsageCard({ d, className }: { d: SystemDashboard; className?: string }) {
  const items = [
    {
      icon: Hash,
      label: "LLM tokens",
      value: formatNumber(d.usage_30d.tokens),
      tone: "text-primary",
    },
    {
      icon: Search,
      label: "KB queries",
      value: formatNumber(d.usage_30d.kb_queries),
      tone: "text-emerald-500",
    },
    {
      icon: MessageSquare,
      label: "Conversations",
      value: formatNumber(d.usage_30d.conversations),
      tone: "text-violet-500",
    },
    {
      icon: Activity,
      label: "Workspaces",
      value: formatNumber(d.resources.workspaces),
      tone: "text-amber-500",
    },
  ];
  return (
    <div className={cn("rounded-xl border border-border bg-card p-5", className)}>
      <h3 className="text-sm font-semibold">Activity (30d)</h3>
      <p className="text-[11px] text-muted-foreground">
        Aggregate across every org. Resets nightly.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {items.map((it) => {
          const Icon = it.icon;
          return (
            <div key={it.label} className="rounded-lg border border-border bg-background px-3 py-2.5">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {it.label}
                </p>
                <Icon className={cn("h-3.5 w-3.5", it.tone)} />
              </div>
              <p className="mt-1 text-lg font-bold tabular-nums">{it.value}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Top orgs by usage ──────────────────────────────────────── */

function TopOrgsCard({ d, className }: { d: SystemDashboard; className?: string }) {
  const max = Math.max(...d.top_orgs_by_tokens_30d.map((o) => o.tokens), 1);
  return (
    <div className={cn("rounded-xl border border-border bg-card p-5", className)}>
      <h3 className="text-sm font-semibold">Top orgs by LLM tokens (30d)</h3>
      {d.top_orgs_by_tokens_30d.length === 0 ? (
        <p className="mt-4 text-xs text-muted-foreground">
          No token usage in the last 30 days.
        </p>
      ) : (
        <ol className="mt-4 space-y-2">
          {d.top_orgs_by_tokens_30d.map((o, i) => {
            const pct = (o.tokens / max) * 100;
            return (
              <li key={o.id} className="text-xs">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="w-4 text-[10px] tabular-nums text-muted-foreground">
                      {i + 1}.
                    </span>
                    <span className="truncate font-medium text-foreground">{o.name}</span>
                    <span className="rounded bg-muted px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-muted-foreground">
                      {o.plan}
                    </span>
                  </span>
                  <span className="tabular-nums text-muted-foreground">
                    {formatNumber(o.tokens)}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}

/* ─── Contracts placeholder ──────────────────────────────────── */

function ContractsCard({ d }: { d: SystemDashboard }) {
  const placeholder = !d.contracts.available;
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-sm font-semibold">Contracts</h3>
          <p className="text-[11px] text-muted-foreground">
            {placeholder ? "Module not yet built" : "Active enterprise agreements"}
          </p>
        </div>
        <FileText className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="mt-5 space-y-3">
        <ContractTile
          label="Active"
          value={placeholder ? "—" : String(d.contracts.active)}
          dim={placeholder}
        />
        <ContractTile
          label="Expiring (30d)"
          value={placeholder ? "—" : String(d.contracts.expiring_30d)}
          dim={placeholder}
        />
        <ContractTile
          label="Total value"
          value={placeholder ? "—" : formatUSD(d.contracts.total_value_cents)}
          dim={placeholder}
        />
      </div>
      {placeholder && (
        <p className="mt-4 rounded-md border border-dashed border-border bg-muted/30 p-2 text-[10px] leading-relaxed text-muted-foreground">
          Schema designed (see <code className="font-mono">docs/architecture/contracts-design</code>),
          implementation deferred until first enterprise deal.
        </p>
      )}
    </div>
  );
}

function ContractTile({
  label,
  value,
  dim,
}: {
  label: string;
  value: string;
  dim?: boolean;
}) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span
        className={cn(
          "tabular-nums font-bold",
          dim ? "text-muted-foreground/40" : "text-foreground",
        )}
      >
        {value}
      </span>
    </div>
  );
}

/* ─── Revenue breakdown ──────────────────────────────────────── */

function RevenueBreakdownCard({ d }: { d: SystemDashboard }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h3 className="text-sm font-semibold">Revenue breakdown</h3>
      <p className="text-[11px] text-muted-foreground">
        MRR is estimated from plan × live-sub count. Hub totals are real
        collected revenue from <code>agent_template_purchases</code>.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <RevTile
          icon={DollarSign}
          label="MRR (subscriptions)"
          value={formatUSD(d.revenue.mrr_usd_cents)}
        />
        <RevTile
          icon={DollarSign}
          label="ARR (12 × MRR)"
          value={formatUSD(d.revenue.mrr_usd_cents * 12)}
        />
        <RevTile
          icon={ShoppingBag}
          label="Hub revenue (all-time)"
          value={formatUSD(d.revenue.hub_total_cents)}
          sub={`${d.revenue.hub_total_purchases} purchases`}
        />
        <RevTile
          icon={ShoppingBag}
          label="Hub revenue (30d)"
          value={formatUSD(d.revenue.hub_30d_cents)}
          sub={`${d.revenue.hub_30d_purchases} purchases`}
        />
      </div>
    </div>
  );
}

function RevTile({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-background px-3 py-3">
      <div className="flex items-center gap-2">
        <Icon className="h-3.5 w-3.5 text-muted-foreground" />
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
      </div>
      <p className="mt-1.5 text-lg font-bold tabular-nums text-foreground">{value}</p>
      {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  );
}

/* ─── Helpers ────────────────────────────────────────────────── */

function formatUSD(cents: number): string {
  if (cents === 0) return "$0";
  const dollars = cents / 100;
  if (dollars >= 1000) return `$${(dollars / 1000).toFixed(1)}K`;
  return `$${dollars.toFixed(dollars % 1 === 0 ? 0 : 2)}`;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
