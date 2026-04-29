"use client";

import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Cpu,
  DollarSign,
  Loader2,
  MessagesSquare,
  Sparkles,
} from "lucide-react";
import { formatPrice } from "@/features/hub/lib/price";
import { useAgents } from "@/features/agents/hooks/useAgents";
import { useDashboard } from "../hooks/useDashboard";
import type { CurrencyRevenue, TokensByModel } from "../services/dashboardService";

/**
 * Authenticated home — single round-trip via /me/dashboard. Empty-account
 * states (no agents, no conversations, no revenue) are handled per-card so
 * a brand-new user sees friendly CTAs instead of "0"s.
 */
export function HomeView() {
  const { data: dash, isLoading } = useDashboard();
  // Existing list query keeps the sidebar fresh and serves the empty-state
  // CTA on this page; cheap because TanStack dedupes the request across hooks.
  const { data: agentsList } = useAgents();

  if (isLoading || !dash) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const isFirstRun = dash.agents.total === 0 && (agentsList?.length ?? 0) === 0;

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <header className="mb-8">
        <h1 className="font-heading text-2xl font-semibold tracking-tight">Home</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Your activity at a glance — agents, conversations, model usage, and
          marketplace revenue.
        </p>
      </header>

      {isFirstRun ? <FirstRunCTA /> : null}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          icon={Bot}
          label="Agents"
          value={dash.agents.total}
          hint={renderAgentBreakdown(dash.agents.by_status)}
          href="/libraries"
        />
        <StatCard
          icon={MessagesSquare}
          label="Conversations"
          value={dash.conversations.total}
          hint={`+${dash.conversations.last_30d} in last 30d`}
        />
        <StatCard
          icon={Cpu}
          label="Tokens used"
          value={formatTokens(dash.tokens.total)}
          hint={`${dash.tokens.by_model.length} model${dash.tokens.by_model.length === 1 ? "" : "s"}`}
        />
        <StatCard
          icon={DollarSign}
          label="Sales (paid)"
          value={dash.revenue.total_paid}
          hint={renderRevenueHint(dash.revenue.by_currency)}
          href="/settings/payouts"
        />
      </div>

      <section className="mt-8 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TokensPanel models={dash.tokens.by_model} total={dash.tokens.total} />
        <RevenuePanel
          rows={dash.revenue.by_currency}
          totalPaid={dash.revenue.total_paid}
          totalRefunded={dash.revenue.total_refunded}
        />
      </section>
    </div>
  );
}

// ─── Cards ──────────────────────────────────────────────────────────

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  href,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  hint?: string;
  href?: string;
}) {
  const body = (
    <div className="rounded-xl border border-border bg-card p-4 transition-colors group-hover:border-primary/30">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="mt-1 text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
  if (href) {
    return (
      <Link href={href} className="group block">
        {body}
      </Link>
    );
  }
  return body;
}

function FirstRunCTA() {
  return (
    <div className="mb-6 flex items-start gap-3 rounded-xl border border-violet-500/30 bg-violet-500/5 p-4 text-sm">
      <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-violet-500" />
      <div className="flex-1">
        <p className="font-medium text-foreground">No agents yet — pick a starter to get going.</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          Five official templates cover the common cases (research, code review,
          KB-powered support, …).
        </p>
        <Link
          href="/welcome"
          className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-violet-600 dark:text-violet-300 hover:underline"
        >
          Open the welcome wizard
          <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}

function TokensPanel({ models, total }: { models: TokensByModel[]; total: number }) {
  if (models.length === 0) {
    return (
      <PanelShell title="Tokens by model">
        <p className="text-xs text-muted-foreground">
          No model usage yet. Once your agents start chatting, the per-model
          breakdown will appear here.
        </p>
      </PanelShell>
    );
  }

  // Inline bar chart — width proportional to share of the top model so the
  // smallest entries are still visible.
  const max = Math.max(...models.map((m) => m.tokens), 1);
  return (
    <PanelShell title="Tokens by model" hint={`${formatTokens(total)} total`}>
      <ul className="space-y-2.5">
        {models.map((m) => {
          const pct = (m.tokens / max) * 100;
          return (
            <li key={m.model}>
              <div className="flex items-baseline justify-between text-[11px]">
                <span className="truncate font-medium" title={m.model}>
                  {m.model}
                </span>
                <span className="text-muted-foreground">{formatTokens(m.tokens)}</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-violet-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </PanelShell>
  );
}

function RevenuePanel({
  rows,
  totalPaid,
  totalRefunded,
}: {
  rows: CurrencyRevenue[];
  totalPaid: number;
  totalRefunded: number;
}) {
  if (rows.length === 0) {
    return (
      <PanelShell title="Marketplace revenue">
        <p className="text-xs text-muted-foreground">
          No paid sales yet. Publish a paid template from your library — pricing
          appears in the publish dialog.
        </p>
      </PanelShell>
    );
  }

  return (
    <PanelShell
      title="Marketplace revenue"
      hint={
        totalRefunded > 0
          ? `${totalPaid} paid · ${totalRefunded} refunded`
          : `${totalPaid} paid`
      }
    >
      <ul className="space-y-3">
        {rows.map((r) => (
          <li
            key={r.currency}
            className="flex items-baseline justify-between border-b border-border last:border-b-0 pb-2 last:pb-0"
          >
            <div>
              <p className="text-xs font-semibold">{r.currency}</p>
              <p className="text-[10px] text-muted-foreground">
                {r.count} sale{r.count === 1 ? "" : "s"}
                {r.fees_cents > 0 && (
                  <>
                    {" · fees "}
                    <span className="text-muted-foreground/70">
                      −{formatPrice(r.fees_cents, r.currency)}
                    </span>
                  </>
                )}
              </p>
            </div>
            <p className="font-mono text-sm font-semibold">
              {formatPrice(r.net_cents, r.currency)}
            </p>
          </li>
        ))}
      </ul>
      <Link
        href="/settings/payouts"
        className="mt-3 inline-flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
      >
        Open payment history
        <ArrowRight className="h-3 w-3" />
      </Link>
    </PanelShell>
  );
}

function PanelShell({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <header className="mb-4 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold">{title}</h2>
        {hint && <span className="text-[10px] text-muted-foreground">{hint}</span>}
      </header>
      {children}
    </section>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────

function formatTokens(n: number): string {
  if (n < 1_000) return n.toString();
  if (n < 1_000_000) return `${(n / 1_000).toFixed(1)}k`;
  return `${(n / 1_000_000).toFixed(2)}M`;
}

function renderAgentBreakdown(byStatus: Record<string, number>): string | undefined {
  const parts = Object.entries(byStatus)
    .filter(([, count]) => count > 0)
    .map(([status, count]) => `${count} ${status}`);
  return parts.length > 0 ? parts.join(" · ") : undefined;
}

function renderRevenueHint(rows: CurrencyRevenue[]): string | undefined {
  if (rows.length === 0) return undefined;
  return rows
    .map((r) => `${formatPrice(r.net_cents, r.currency)} ${r.currency}`)
    .join(" · ");
}
