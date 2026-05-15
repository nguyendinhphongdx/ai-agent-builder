"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  CreditCard,
  ExternalLink,
  Loader2,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { StatusBadge, type StatusTone } from "@/components/ui/status-badge";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import {
  billingService,
  type BillingOverview,
  type PlanInfo,
  type QuotaUsage,
} from "@/lib/api/billingService";

/**
 * Billing & plan dashboard. One screen:
 *   - Current plan card (status, renews-on, manage portal).
 *   - Usage progress bars (tokens + KB queries) vs plan limit.
 *   - Plan picker: shows self-serve plans, button is "Switch to X"
 *     (or "Current" if active). Click → POST /billing/checkout →
 *     redirect to Stripe-hosted Checkout.
 *
 * Stripe-not-configured deployments still see this page — the
 * portal/upgrade buttons surface a clear "billing is disabled"
 * state instead of 500ing.
 */
export function BillingView() {
  const qc = useQueryClient();

  const subQ = useQuery({
    queryKey: ["billing-subscription"],
    queryFn: () => billingService.getSubscription(),
  });

  const plansQ = useQuery({
    queryKey: ["billing-plans"],
    queryFn: () => billingService.listPlans(),
  });

  const checkoutM = useMutation({
    mutationFn: (planCode: string) => billingService.checkout(planCode),
    onSuccess: (data) => {
      // Stripe checkout is full-page — the user comes back to
      // /org/billing?ok=1 after success; the webhook lands
      // the row before then in most cases.
      window.location.href = data.url;
    },
  });

  const portalM = useMutation({
    mutationFn: () => billingService.portal(),
    onSuccess: (data) => {
      window.location.href = data.url;
    },
  });

  return (
    <div className="mx-auto max-w-4xl p-6">
      <SettingsPageHeader
        title="Billing & Plan"
        description="Switch plans, manage payment method, monitor usage against your monthly cap."
      />

      <SettingsStack>
        <CurrentPlanCard
          overview={subQ.data}
          loading={subQ.isLoading}
          onManage={() => portalM.mutate()}
          portalLoading={portalM.isPending}
        />

        <UsageCard overview={subQ.data} loading={subQ.isLoading} />

        <PlanPickerCard
          plans={plansQ.data ?? []}
          currentPlanCode={subQ.data?.subscription.plan.code}
          onSelect={(code) => checkoutM.mutate(code)}
          loading={plansQ.isLoading}
          checkoutLoading={checkoutM.isPending}
          pendingCode={checkoutM.variables}
        />
      </SettingsStack>
    </div>
  );
}

/* ─── Current plan ─────────────────────────────────────────── */

function CurrentPlanCard({
  overview,
  loading,
  onManage,
  portalLoading,
}: {
  overview: BillingOverview | undefined;
  loading: boolean;
  onManage: () => void;
  portalLoading: boolean;
}) {
  if (loading || !overview) {
    return (
      <div className="h-32 animate-pulse rounded-xl border border-border bg-muted/30" />
    );
  }
  const { plan, status, current_period_end, cancel_at_period_end, has_stripe_subscription } =
    overview.subscription;
  return (
    <SettingsCard title="Current plan">
      <div className="flex flex-wrap items-start justify-between gap-4 p-5">
        <div>
          <div className="flex items-baseline gap-3">
            <span className="text-2xl font-semibold">{plan.name}</span>
            <SubscriptionStatusBadge status={status} />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {has_stripe_subscription
              ? cancel_at_period_end
                ? `Cancels at end of period · ${formatDate(current_period_end)}`
                : `Renews on ${formatDate(current_period_end)}`
              : "No paid subscription. Free-tier limits apply."}
          </p>
        </div>
        {has_stripe_subscription && (
          <button
            type="button"
            onClick={onManage}
            disabled={portalLoading}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-background px-3 py-1.5 text-xs font-medium transition-colors hover:bg-accent disabled:opacity-50"
          >
            {portalLoading ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <CreditCard className="h-3 w-3" />
            )}
            Manage billing
            <ExternalLink className="h-3 w-3 opacity-50" />
          </button>
        )}
      </div>
    </SettingsCard>
  );
}

function SubscriptionStatusBadge({ status }: { status: string }) {
  const { tone, label, icon } = subscriptionStatusVisual(status);
  return (
    <StatusBadge tone={tone}>
      {icon}
      <span className="uppercase tracking-wider">{label}</span>
    </StatusBadge>
  );
}

function subscriptionStatusVisual(status: string): {
  tone: StatusTone;
  label: string;
  icon?: React.ReactNode;
} {
  switch (status) {
    case "past_due":
      return {
        tone: "pending",
        label: "payment failed",
        icon: <AlertTriangle className="h-3 w-3" />,
      };
    case "canceled":
      return { tone: "failed", label: "canceled" };
    case "trialing":
      return { tone: "info", label: "trialing" };
    case "active":
      return {
        tone: "active",
        label: "active",
        icon: <CheckCircle2 className="h-3 w-3" />,
      };
    default:
      return { tone: "inactive", label: status };
  }
}

/* ─── Usage bars ───────────────────────────────────────────── */

function UsageCard({
  overview,
  loading,
}: {
  overview: BillingOverview | undefined;
  loading: boolean;
}) {
  if (loading || !overview) {
    return (
      <div className="h-32 animate-pulse rounded-xl border border-border bg-muted/30" />
    );
  }
  return (
    <SettingsCard
      title="Usage this period"
      description="Aggregated across every workspace in your organization."
    >
      <div className="space-y-5 p-5">
        <QuotaBar
          label="LLM tokens"
          quota={overview.tokens}
          formatter={(n) =>
            n >= 1_000_000
              ? `${(n / 1_000_000).toFixed(2)}M`
              : n >= 1_000
                ? `${(n / 1_000).toFixed(1)}k`
                : n.toLocaleString()
          }
        />
        <QuotaBar
          label="KB queries"
          quota={overview.kb_queries}
          formatter={(n) => n.toLocaleString()}
        />
      </div>
    </SettingsCard>
  );
}

function QuotaBar({
  label,
  quota,
  formatter,
}: {
  label: string;
  quota: QuotaUsage;
  formatter: (n: number) => string;
}) {
  const unlimited = quota.limit === 0;
  const danger = quota.pct >= 90;
  const warn = !danger && quota.pct >= 75;
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between text-xs">
        <span className="font-medium">{label}</span>
        <span className="font-mono tabular-nums text-muted-foreground">
          {formatter(quota.used)}
          {unlimited ? " / ∞" : ` / ${formatter(quota.limit)}`}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted/60">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            unlimited
              ? "bg-info/60"
              : danger
                ? "bg-destructive"
                : warn
                  ? "bg-warning"
                  : "bg-success",
          )}
          style={{ width: unlimited ? "10%" : `${Math.max(2, quota.pct)}%` }}
        />
      </div>
    </div>
  );
}

/* ─── Plan picker ──────────────────────────────────────────── */

function PlanPickerCard({
  plans,
  currentPlanCode,
  onSelect,
  loading,
  checkoutLoading,
  pendingCode,
}: {
  plans: PlanInfo[];
  currentPlanCode: string | undefined;
  onSelect: (planCode: string) => void;
  loading: boolean;
  checkoutLoading: boolean;
  pendingCode: string | undefined;
}) {
  if (loading) {
    return (
      <div className="h-40 animate-pulse rounded-xl border border-border bg-muted/30" />
    );
  }
  if (plans.length === 0) {
    return (
      <SettingsCard title="Plans">
        <p className="px-5 py-6 text-xs text-muted-foreground">
          Billing is not configured for this deployment. Free-tier limits apply.
        </p>
      </SettingsCard>
    );
  }
  return (
    <SettingsCard
      title="Switch plans"
      description="Pick a plan and pay through Stripe. Switching takes effect immediately."
    >
      <div className="grid gap-3 p-5 md:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = currentPlanCode === plan.code;
          const isPending = checkoutLoading && pendingCode === plan.code;
          return (
            <div
              key={plan.code}
              className={cn(
                "flex flex-col rounded-xl border bg-background p-4",
                isCurrent
                  ? "border-primary/60 ring-1 ring-primary/30"
                  : "border-border",
              )}
            >
              <div className="mb-3 flex items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                <span className="text-sm font-semibold">{plan.name}</span>
              </div>
              <ul className="mb-4 flex-1 space-y-1.5 text-[11px] text-muted-foreground">
                <li>
                  <span className="font-mono text-foreground">
                    {fmtCap(plan.monthly_llm_tokens)}
                  </span>{" "}
                  tokens / mo
                </li>
                <li>
                  <span className="font-mono text-foreground">
                    {fmtCap(plan.monthly_kb_queries)}
                  </span>{" "}
                  KB queries / mo
                </li>
                <li>
                  <span className="font-mono text-foreground">
                    {fmtCap(plan.max_members)}
                  </span>{" "}
                  members
                </li>
                <li>
                  <span className="font-mono text-foreground">
                    {fmtCap(plan.max_workspaces)}
                  </span>{" "}
                  workspaces
                </li>
                {plan.features.sso === true && <li>✓ SSO (SAML / OIDC)</li>}
                {plan.features.custom_roles === true && <li>✓ Custom roles</li>}
                {plan.features.trace_provider === true && (
                  <li>✓ LLM trace platform export</li>
                )}
              </ul>
              <button
                type="button"
                onClick={() => onSelect(plan.code)}
                disabled={isCurrent || isPending}
                className={cn(
                  "inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  isCurrent
                    ? "bg-muted/60 text-muted-foreground"
                    : "bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50",
                )}
              >
                {isPending ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : null}
                {isCurrent ? "Current plan" : `Switch to ${plan.name}`}
              </button>
            </div>
          );
        })}
      </div>
    </SettingsCard>
  );
}

/* ─── Helpers ──────────────────────────────────────────────── */

function fmtCap(n: number): string {
  if (n === 0) return "∞";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(n % 1_000_000 ? 1 : 0)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(n % 1_000 ? 1 : 0)}k`;
  return n.toLocaleString();
}

function formatDate(s: string | null): string {
  if (!s) return "—";
  try {
    return new Date(s).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return s;
  }
}
