"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CreditCard,
  Loader2,
  PauseCircle,
  Search,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  systemSubscriptionsService,
  type SystemSubscriptionRow,
} from "@/lib/api/systemSubscriptionsService";
import { useSystemAccess } from "../hooks/useSystemAccess";

/** Page body for /system/subscriptions. */
export function SubscriptionsView() {
  const { canWrite } = useSystemAccess();
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [detailOrgId, setDetailOrgId] = useState<string | null>(null);

  const statsQ = useQuery({
    queryKey: ["system", "subscriptions", "stats"],
    queryFn: () => systemSubscriptionsService.stats(),
    staleTime: 30_000,
  });

  const listQ = useQuery({
    queryKey: ["system", "subscriptions", { planFilter, statusFilter }],
    queryFn: () =>
      systemSubscriptionsService.list({
        plan: planFilter ?? undefined,
        status: statusFilter ?? undefined,
      }),
    staleTime: 10_000,
  });

  const rows = listQ.data?.rows ?? [];
  // Client-side text search on top of the server filter — cheap, and
  // search is what people type while clicking filter buttons anyway.
  const filtered = search
    ? rows.filter(
        (r) =>
          r.org_name.toLowerCase().includes(search.toLowerCase()) ||
          r.org_slug.toLowerCase().includes(search.toLowerCase()),
      )
    : rows;

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <header>
        <h1 className="text-xl font-bold tracking-tight">Subscriptions</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Every org&apos;s billing state. Orgs without a sub row sit on their
          ``organizations.plan`` default (usually free).
        </p>
      </header>

      <StatsRow stats={statsQ.data} loading={statsQ.isLoading} />

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search org name or slug…"
            className="h-8 pl-8 text-xs"
          />
        </div>
        <FilterChips
          label="Plan"
          options={Object.keys(statsQ.data?.by_plan ?? {}).sort()}
          active={planFilter}
          onChange={setPlanFilter}
        />
        <FilterChips
          label="Status"
          options={Object.keys(statsQ.data?.by_status ?? {}).sort()}
          active={statusFilter}
          onChange={setStatusFilter}
        />
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-border">
        {listQ.isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          </div>
        ) : filtered.length === 0 ? (
          <p className="px-4 py-12 text-center text-xs text-muted-foreground">
            No subscriptions match.
          </p>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left font-semibold">Org</th>
                <th className="px-4 py-2 text-left font-semibold">Plan</th>
                <th className="px-4 py-2 text-left font-semibold">Status</th>
                <th className="px-4 py-2 text-left font-semibold">Period end</th>
                <th className="px-4 py-2 text-left font-semibold">Source</th>
                <th className="px-4 py-2" aria-hidden="true" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <SubRow
                  key={row.org_id}
                  row={row}
                  onOpen={() => setDetailOrgId(row.org_id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {detailOrgId && (
        <SubscriptionDetailSheet
          orgId={detailOrgId}
          onClose={() => setDetailOrgId(null)}
          canWrite={canWrite}
        />
      )}
    </div>
  );
}

/* ─── Stats row ──────────────────────────────────────────────── */

function StatsRow({
  stats,
  loading,
}: {
  stats: { total_orgs: number; live_subs: number; trialing: number; cancel_scheduled: number } | undefined;
  loading: boolean;
}) {
  const tiles = [
    { label: "Total orgs", value: stats?.total_orgs ?? "—", icon: CreditCard, tone: "text-foreground" },
    { label: "Live subs", value: stats?.live_subs ?? "—", icon: CreditCard, tone: "text-emerald-500" },
    { label: "Trialing", value: stats?.trialing ?? "—", icon: PauseCircle, tone: "text-amber-500" },
    { label: "Cancel scheduled", value: stats?.cancel_scheduled ?? "—", icon: XCircle, tone: "text-rose-500" },
  ];
  return (
    <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((t) => {
        const Icon = t.icon;
        return (
          <div
            key={t.label}
            className="rounded-lg border border-border bg-card px-4 py-3"
          >
            <div className="flex items-center justify-between">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                {t.label}
              </p>
              <Icon className={cn("h-3.5 w-3.5", t.tone)} />
            </div>
            <p className="mt-1 text-xl font-bold tabular-nums text-foreground">
              {loading ? "…" : t.value}
            </p>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Filter chips ───────────────────────────────────────────── */

function FilterChips({
  label,
  options,
  active,
  onChange,
}: {
  label: string;
  options: string[];
  active: string | null;
  onChange: (next: string | null) => void;
}) {
  if (options.length === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}:
      </span>
      <button
        type="button"
        onClick={() => onChange(null)}
        className={cn(
          "rounded-full px-2 py-0.5 text-[11px] font-medium transition-colors",
          active === null
            ? "bg-foreground text-background"
            : "border border-border text-muted-foreground hover:bg-muted",
        )}
      >
        all
      </button>
      {options.map((o) => (
        <button
          key={o}
          type="button"
          onClick={() => onChange(o === active ? null : o)}
          className={cn(
            "rounded-full px-2 py-0.5 text-[11px] font-medium transition-colors",
            o === active
              ? "bg-foreground text-background"
              : "border border-border text-muted-foreground hover:bg-muted",
          )}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

/* ─── Table row ──────────────────────────────────────────────── */

function SubRow({ row, onOpen }: { row: SystemSubscriptionRow; onOpen: () => void }) {
  return (
    <tr
      onClick={onOpen}
      className="cursor-pointer border-t border-border transition-colors hover:bg-muted/30"
    >
      <td className="px-4 py-2">
        <div className="font-medium text-foreground">{row.org_name}</div>
        <div className="font-mono text-[10px] text-muted-foreground">{row.org_slug}</div>
      </td>
      <td className="px-4 py-2">
        <PlanBadge plan={row.plan_code} />
      </td>
      <td className="px-4 py-2">
        <StatusBadge status={row.status} live={row.is_live} />
        {row.cancel_at_period_end && (
          <span className="ml-1.5 inline-flex items-center gap-1 rounded bg-rose-500/10 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-rose-600 dark:text-rose-400">
            <AlertTriangle className="h-2.5 w-2.5" />
            ending
          </span>
        )}
      </td>
      <td className="px-4 py-2 text-[11px] text-muted-foreground">
        {row.current_period_end ? new Date(row.current_period_end).toLocaleDateString() : "—"}
      </td>
      <td className="px-4 py-2 text-[11px] text-muted-foreground">
        {row.stripe_subscription_id ? "Stripe" : row.status === "none" ? "default" : "manual"}
      </td>
      <td className="px-4 py-2 text-right text-[11px] text-muted-foreground">›</td>
    </tr>
  );
}

function PlanBadge({ plan }: { plan: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        plan === "enterprise"
          ? "bg-violet-500/10 text-violet-600 dark:text-violet-400"
          : plan === "pro"
            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
            : plan === "starter"
              ? "bg-sky-500/10 text-sky-600 dark:text-sky-400"
              : "bg-muted text-muted-foreground",
      )}
    >
      {plan}
    </span>
  );
}

function StatusBadge({ status, live }: { status: string; live: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
        live
          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
          : status === "past_due"
            ? "bg-rose-500/10 text-rose-600 dark:text-rose-400"
            : status === "trialing"
              ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
              : "bg-muted text-muted-foreground",
      )}
    >
      {status}
    </span>
  );
}

/* ─── Detail sheet ────────────────────────────────────────────── */

const PLAN_CHOICES = ["free", "starter", "pro", "enterprise"];

function SubscriptionDetailSheet({
  orgId,
  onClose,
  canWrite,
}: {
  orgId: string;
  onClose: () => void;
  canWrite: boolean;
}) {
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["system", "subscriptions", orgId],
    queryFn: () => systemSubscriptionsService.get(orgId),
    staleTime: 5_000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["system", "subscriptions"] });
  };

  const setPlan = useMutation({
    mutationFn: (plan: string) => systemSubscriptionsService.setPlan(orgId, plan),
    onSuccess: () => {
      toast.success("Plan updated");
      invalidate();
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const cancelSub = useMutation({
    mutationFn: (immediate: boolean) =>
      systemSubscriptionsService.cancel(orgId, { immediate }),
    onSuccess: (_, immediate) => {
      toast.success(immediate ? "Canceled immediately" : "Cancel at period end scheduled");
      invalidate();
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const row = q.data;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/40"
      onClick={onClose}
    >
      <aside
        className="h-full w-full max-w-md overflow-y-auto border-l border-border bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {q.isLoading ? (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        ) : !row ? (
          <p className="text-sm text-muted-foreground">Not found.</p>
        ) : (
          <>
            <header className="border-b border-border pb-4">
              <h2 className="text-base font-semibold">{row.org_name}</h2>
              <p className="font-mono text-[11px] text-muted-foreground">{row.org_slug}</p>
            </header>

            <dl className="mt-4 space-y-3 text-xs">
              <Field label="Plan" value={<PlanBadge plan={row.plan_code} />} />
              <Field
                label="Status"
                value={<StatusBadge status={row.status} live={row.is_live} />}
              />
              <Field
                label="Period end"
                value={
                  row.current_period_end
                    ? new Date(row.current_period_end).toLocaleString()
                    : "—"
                }
              />
              <Field
                label="Cancel at period end"
                value={row.cancel_at_period_end ? "Yes" : "No"}
              />
              <Field
                label="Stripe subscription"
                value={
                  row.stripe_subscription_id ? (
                    <span className="font-mono text-[10px]">
                      {row.stripe_subscription_id}
                    </span>
                  ) : (
                    "—"
                  )
                }
              />
            </dl>

            {canWrite && (
              <div className="mt-6 space-y-4 border-t border-border pt-4">
                <div className="space-y-1.5">
                  <Label className="text-[11px]">Override plan</Label>
                  <div className="flex flex-wrap gap-1.5">
                    {PLAN_CHOICES.map((p) => (
                      <Button
                        key={p}
                        size="sm"
                        variant={p === row.plan_code ? "default" : "outline"}
                        disabled={setPlan.isPending || p === row.plan_code}
                        onClick={() => setPlan.mutate(p)}
                      >
                        {p}
                      </Button>
                    ))}
                  </div>
                  <p className="text-[10px] text-muted-foreground">
                    Bypasses Stripe. Use for comps, trials, enterprise deals
                    signed offline.
                  </p>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-[11px]">Cancel</Label>
                  <div className="flex flex-wrap gap-1.5">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={cancelSub.isPending}
                      onClick={() => cancelSub.mutate(false)}
                    >
                      End of period
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      disabled={cancelSub.isPending}
                      onClick={() => {
                        if (confirm("Cancel immediately? User loses access now.")) {
                          cancelSub.mutate(true);
                        }
                      }}
                    >
                      Immediate
                    </Button>
                  </div>
                </div>
              </div>
            )}

            <div className="mt-6 flex justify-end">
              <Button variant="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-[11px] uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="text-right text-foreground">{value}</dd>
    </div>
  );
}

function extractMsg(err: unknown): string {
  const anyErr = err as { response?: { data?: { detail?: unknown } }; message?: string };
  const d = anyErr?.response?.data?.detail;
  if (typeof d === "string") return d;
  return anyErr?.message ?? "Request failed";
}
