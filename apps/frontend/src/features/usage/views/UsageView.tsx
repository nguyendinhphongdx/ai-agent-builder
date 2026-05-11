"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { DollarSign, Hash, Loader2, Timer, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import {
  usageService,
  type UsageDailyPoint,
} from "@/lib/api/usageService";

const RANGE_PRESETS = [
  { label: "7d", days: 7 },
  { label: "30d", days: 30 },
  { label: "90d", days: 90 },
] as const;

/**
 * Workspace cost dashboard. Three sections:
 *   - Stat cards (totals over the selected range).
 *   - Daily cost trend — ASCII-bar chart so it's dep-free.
 *     Drop in recharts later if/when other charts ship.
 *   - Spend by provider/model table.
 *
 * Reads ``/api/usage/*`` which uses the active workspace from the
 * X-Workspace-Id header — switching workspaces in the header
 * switcher auto-refetches everything.
 */
export function UsageView() {
  const [days, setDays] = useState<number>(30);

  const since = useMemo(() => {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - days);
    return d.toISOString();
  }, [days]);

  const params = { since };

  const totals = useQuery({
    queryKey: ["usage-totals", since],
    queryFn: () => usageService.totals(params),
  });

  const daily = useQuery({
    queryKey: ["usage-daily", since],
    queryFn: () => usageService.daily(params),
  });

  const byModel = useQuery({
    queryKey: ["usage-by-model", since],
    queryFn: () => usageService.byModel(params),
  });

  return (
    <div className="mx-auto max-w-5xl p-6">
      <SettingsPageHeader
        title="Usage & cost"
        description="Token consumption + LLM spend across this workspace. Updated after each chat turn."
        action={
          <div className="inline-flex rounded-md border border-border bg-muted/30 p-0.5">
            {RANGE_PRESETS.map((r) => (
              <button
                key={r.label}
                type="button"
                onClick={() => setDays(r.days)}
                className={cn(
                  "px-2.5 py-1 text-[11px] font-medium rounded transition-colors",
                  days === r.days
                    ? "bg-background shadow-sm text-foreground"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {r.label}
              </button>
            ))}
          </div>
        }
      />

      <SettingsStack>
        <StatCardsRow loading={totals.isLoading} data={totals.data} />

        <SettingsCard
          title="Daily cost"
          description="USD per UTC day."
        >
          <div className="p-5">
            {daily.isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : (
              <CostBarChart points={daily.data ?? []} />
            )}
          </div>
        </SettingsCard>

        <SettingsCard
          title="Spend by model"
          description="Sorted by total cost. Largest movers at the top."
        >
          {byModel.isLoading ? (
            <div className="p-5">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : !byModel.data || byModel.data.length === 0 ? (
            <p className="px-5 py-8 text-center text-xs text-muted-foreground">
              No LLM calls in the selected window.
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead className="text-[10px] uppercase tracking-wider text-muted-foreground">
                <tr className="border-b border-border">
                  <th className="px-5 py-2 text-left">Provider</th>
                  <th className="px-5 py-2 text-left">Model</th>
                  <th className="px-5 py-2 text-right">Calls</th>
                  <th className="px-5 py-2 text-right">Tokens</th>
                  <th className="px-5 py-2 text-right">Cost</th>
                </tr>
              </thead>
              <tbody>
                {byModel.data.map((row, idx) => (
                  <tr
                    key={`${row.provider}/${row.model}/${idx}`}
                    className="border-b border-border/60 last:border-b-0"
                  >
                    <td className="px-5 py-2 font-medium">
                      {row.provider ?? "—"}
                    </td>
                    <td className="px-5 py-2 font-mono text-[11px]">
                      {row.model ?? "unknown"}
                    </td>
                    <td className="px-5 py-2 text-right tabular-nums">
                      {row.count.toLocaleString()}
                    </td>
                    <td className="px-5 py-2 text-right tabular-nums text-muted-foreground">
                      {row.tokens.toLocaleString()}
                    </td>
                    <td className="px-5 py-2 text-right font-mono text-[11px]">
                      ${row.cost_usd.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SettingsCard>
      </SettingsStack>
    </div>
  );
}

/* ─── Stat cards ────────────────────────────────────────────── */

function StatCardsRow({
  loading,
  data,
}: {
  loading: boolean;
  data: { count: number; tokens: number; cost_usd: number; avg_latency_ms: number } | undefined;
}) {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-20 animate-pulse rounded-xl border border-border bg-muted/30"
          />
        ))}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <StatCard
        icon={DollarSign}
        label="Cost"
        value={`$${data.cost_usd.toFixed(2)}`}
      />
      <StatCard
        icon={Zap}
        label="LLM calls"
        value={data.count.toLocaleString()}
      />
      <StatCard
        icon={Hash}
        label="Tokens"
        value={
          data.tokens >= 1_000_000
            ? `${(data.tokens / 1_000_000).toFixed(2)}M`
            : data.tokens >= 1_000
              ? `${(data.tokens / 1_000).toFixed(1)}k`
              : data.tokens.toLocaleString()
        }
      />
      <StatCard
        icon={Timer}
        label="Avg latency"
        value={`${Math.round(data.avg_latency_ms)}ms`}
      />
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-muted-foreground">
        <Icon className="h-3 w-3" />
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold tabular-nums">{value}</div>
    </div>
  );
}

/* ─── Cost bar chart (dep-free) ─────────────────────────────── */

function CostBarChart({ points }: { points: UsageDailyPoint[] }) {
  if (points.length === 0) {
    return (
      <p className="py-8 text-center text-xs text-muted-foreground">
        No usage in the selected window.
      </p>
    );
  }
  const max = Math.max(...points.map((p) => p.cost_usd), 0.0001);
  return (
    <div className="space-y-1">
      {points.map((p) => (
        <div key={p.day} className="flex items-center gap-3 text-[11px]">
          <span className="w-20 shrink-0 font-mono text-[10px] text-muted-foreground">
            {p.day}
          </span>
          <div className="relative h-3.5 flex-1 overflow-hidden rounded bg-muted/50">
            <div
              className="absolute inset-y-0 left-0 bg-primary/70 transition-all"
              style={{ width: `${Math.max(2, (p.cost_usd / max) * 100)}%` }}
            />
          </div>
          <span className="w-16 shrink-0 text-right font-mono tabular-nums">
            ${p.cost_usd.toFixed(4)}
          </span>
        </div>
      ))}
    </div>
  );
}
