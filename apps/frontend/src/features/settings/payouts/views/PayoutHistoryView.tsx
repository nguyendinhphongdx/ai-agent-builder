"use client";

import { useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatPrice } from "@/features/hub/lib/price";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import { MomoConnectSection } from "../components/MomoConnectSection";
import { PayoutsSection } from "../components/PayoutsSection";
import { usePayoutHistory, usePayoutSummary } from "../hooks/usePayouts";
import type { HistoryParams } from "../services/payoutsService";

const PAGE_SIZE = 50;

/**
 * Author payment history — purchases of templates owned by the current user.
 *
 * Two stacked panels: monthly summary (per currency) at the top, then a
 * paginated table of individual purchases. Filters narrow by status +
 * provider; both filters compose with paging.
 */
export function PayoutHistoryView() {
  const [filters, setFilters] = useState<HistoryParams>({});
  const [page, setPage] = useState(0);

  const params: HistoryParams = {
    ...filters,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  };

  const { data: history, isLoading: historyLoading } = usePayoutHistory(params);
  const { data: summary, isLoading: summaryLoading } = usePayoutSummary();

  const setFilter = <K extends keyof HistoryParams>(
    key: K,
    value: HistoryParams[K] | undefined,
  ) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(0);
  };

  return (
    <div>
      <SettingsPageHeader
        title="Author Payouts"
        description="Connect Stripe (USD/EUR/GBP) and/or MoMo Business (VND) so sale proceeds settle directly to you. Without a connection, sales fall back to platform-collects (we settle you manually)."
      />

      <SettingsStack>
        <PayoutsSection />
        <MomoConnectSection />

        {/* Summary by currency */}
        <SettingsCard
          title="Totals"
          description="Lifetime gross, fees, and net per currency."
        >
          {summaryLoading ? (
            <div className="flex h-24 items-center justify-center">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : !summary || summary.totals.length === 0 ? (
            <p className="text-xs text-muted-foreground">No paid sales yet.</p>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {summary.totals.map((t) => (
                <div
                  key={t.currency}
                  className="rounded-lg border border-border/60 bg-muted/20 p-3"
                >
                  <div className="flex items-baseline justify-between">
                    <span className="text-xs font-semibold text-muted-foreground">
                      {t.currency}
                    </span>
                    <span className="text-[10px] text-muted-foreground/70">
                      {t.count} sale{t.count === 1 ? "" : "s"}
                    </span>
                  </div>
                  <p className="mt-1.5 text-xl font-semibold tracking-tight">
                    {formatPrice(t.net_cents, t.currency)}
                  </p>
                  <p className="mt-0.5 text-[10px] text-muted-foreground">
                    Gross {formatPrice(t.gross_cents, t.currency)}
                    {t.fees_cents > 0 && (
                      <>
                        {" · fees "}
                        −{formatPrice(t.fees_cents, t.currency)}
                      </>
                    )}
                  </p>
                </div>
              ))}
            </div>
          )}

          {summary && summary.by_month.length > 0 && (
            <details className="mt-4 rounded-lg border border-border/60 bg-muted/20">
              <summary className="cursor-pointer px-3 py-2 text-[11px] font-medium text-muted-foreground hover:text-foreground">
                Monthly breakdown ({summary.by_month.length} rows)
              </summary>
              <div className="border-t border-border">
                <table className="w-full text-xs">
                <thead className="bg-muted/30 text-[10px] uppercase tracking-wide text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2 text-left">Month</th>
                    <th className="px-3 py-2 text-left">Currency</th>
                    <th className="px-3 py-2 text-right">Sales</th>
                    <th className="px-3 py-2 text-right">Gross</th>
                    <th className="px-3 py-2 text-right">Fees</th>
                    <th className="px-3 py-2 text-right">Net</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.by_month.map((m, i) => (
                    <tr
                      key={`${m.month}-${m.currency}`}
                      className={i % 2 === 0 ? "bg-background" : "bg-muted/20"}
                    >
                      <td className="px-3 py-1.5">{m.month}</td>
                      <td className="px-3 py-1.5">{m.currency}</td>
                      <td className="px-3 py-1.5 text-right">{m.count}</td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        {formatPrice(m.gross_cents, m.currency)}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono text-muted-foreground">
                        {m.fees_cents > 0
                          ? `−${formatPrice(m.fees_cents, m.currency)}`
                          : "—"}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono font-semibold">
                        {formatPrice(m.net_cents, m.currency)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        )}
        </SettingsCard>

        <SettingsCard
          title="Transactions"
          description="Per-purchase rows. Filter by status or gateway."
          action={
            <div className="flex flex-wrap items-center gap-1.5">
              <FilterPill
                active={!filters.status}
                onClick={() => setFilter("status", undefined)}
                label="All"
              />
              <FilterPill
                active={filters.status === "paid"}
                onClick={() => setFilter("status", "paid")}
                label="Paid"
              />
              <FilterPill
                active={filters.status === "refunded"}
                onClick={() => setFilter("status", "refunded")}
                label="Refunded"
              />
              <span className="text-[10px] text-muted-foreground/40">·</span>
              <FilterPill
                active={!filters.provider}
                onClick={() => setFilter("provider", undefined)}
                label="Any"
              />
              <FilterPill
                active={filters.provider === "stripe"}
                onClick={() => setFilter("provider", "stripe")}
                label="Stripe"
              />
              <FilterPill
                active={filters.provider === "momo"}
                onClick={() => setFilter("provider", "momo")}
                label="MoMo"
              />
            </div>
          }
          bodyClassName="p-0"
        >
        {historyLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : !history || history.items.length === 0 ? (
          <p className="px-5 py-12 text-center text-xs text-muted-foreground">
            No transactions match these filters.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-muted/30 text-[10px] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left">When</th>
                  <th className="px-3 py-2 text-left">Template</th>
                  <th className="px-3 py-2 text-left">Buyer</th>
                  <th className="px-3 py-2 text-left">Provider</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Payout</th>
                  <th className="px-3 py-2 text-right">Gross</th>
                  <th className="px-3 py-2 text-right">Fee</th>
                  <th className="px-3 py-2 text-right">Net</th>
                </tr>
              </thead>
              <tbody>
                {history.items.map((row, i) => (
                  <tr
                    key={row.id}
                    className={i % 2 === 0 ? "bg-background" : "bg-muted/20"}
                  >
                    <td className="px-3 py-2 text-muted-foreground">
                      {new Date(row.purchased_at).toLocaleDateString()}
                    </td>
                    <td className="max-w-[220px] truncate px-3 py-2 font-medium">
                      <Link
                        href={`/hub/${row.template_id}`}
                        className="hover:underline"
                      >
                        {row.template_title}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {row.buyer_email_masked ?? "—"}
                    </td>
                    <td className="px-3 py-2 capitalize">{row.provider}</td>
                    <td className="px-3 py-2">
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="px-3 py-2">
                      <SettlementBadge
                        settledAt={row.settled_at}
                        provider={row.provider}
                        status={row.status}
                      />
                    </td>
                    <td className="px-3 py-2 text-right font-mono">
                      {formatPrice(row.price_paid_cents, row.currency)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-muted-foreground">
                      {row.platform_fee_cents > 0
                        ? `−${formatPrice(row.platform_fee_cents, row.currency)}`
                        : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-mono font-semibold">
                      {formatPrice(row.net_cents, row.currency)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {history && history.total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-border px-5 py-3 text-xs text-muted-foreground">
            <span>
              {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, history.total)}{" "}
              of {history.total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => Math.max(0, p - 1))}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!history.has_more}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
        </SettingsCard>
      </SettingsStack>
    </div>
  );
}

function FilterPill({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        active
          ? "rounded-full border border-primary bg-primary/10 px-2.5 py-1 text-[11px] font-medium text-foreground"
          : "rounded-full border border-border bg-background px-2.5 py-1 text-[11px] text-muted-foreground hover:border-foreground/30 hover:text-foreground"
      }
    >
      {label}
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "paid"
      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
      : status === "refunded"
        ? "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300"
        : "border-border bg-muted text-muted-foreground";
  return (
    <Badge variant="outline" className={`text-[10px] ${cls}`}>
      {status}
    </Badge>
  );
}

function SettlementBadge({
  settledAt,
  provider,
  status,
}: {
  settledAt: string | null;
  provider: string;
  status: string;
}) {
  // Refunded rows don't owe a payout — collapse to a dash so authors
  // don't expect money.
  if (status === "refunded") {
    return <span className="text-[11px] text-muted-foreground/60">—</span>;
  }
  if (settledAt) {
    return (
      <Badge
        variant="outline"
        className="border-emerald-500/40 bg-emerald-500/10 text-[10px] text-emerald-700 dark:text-emerald-300"
        title={`Settled ${new Date(settledAt).toLocaleString()}`}
      >
        Settled
      </Badge>
    );
  }
  // MoMo rows wait for ops to mark — surface that explicitly so authors
  // know what they're waiting for. Stripe rows that aren't settled yet
  // are mid-flight (rare) so we show "pending".
  return (
    <Badge
      variant="outline"
      className="border-amber-500/40 bg-amber-500/10 text-[10px] text-amber-700 dark:text-amber-300"
      title={
        provider === "momo"
          ? "Awaiting manual settlement from the platform"
          : "Stripe is processing the transfer"
      }
    >
      Pending
    </Badge>
  );
}
