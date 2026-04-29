"use client";

import Link from "next/link";
import { ArrowRight, Banknote, ExternalLink, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  useDashboardLink,
  usePayoutStatus,
  useStartOnboarding,
} from "../hooks/usePayouts";

/** Settings panel for Stripe Connect onboarding. Shown to every user; we
 *  don't gate on a "creator" flag — anyone can publish a paid template,
 *  they just need to onboard first. */
export function PayoutsSection() {
  const { data: status, isLoading, refetch } = usePayoutStatus();
  const onboarding = useStartOnboarding();
  const dashboard = useDashboardLink();

  const ready = !!status?.charges_enabled && !!status?.payouts_enabled;
  const partial = !!status?.connected && !ready;

  return (
    <section>
      <div className="mb-4">
        <h2 className="text-base font-semibold">Author Payouts</h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Connect a Stripe payout account to sell paid templates on the Hub.
          Free templates don&apos;t need this.
        </p>
      </div>

      <div className="rounded-xl border border-border bg-muted/30 p-4">
        <div className="flex items-start gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
            <Banknote className="h-4 w-4 text-muted-foreground" />
          </div>

          <div className="flex-1">
            <PayoutStatusLabel
              isLoading={isLoading}
              connected={!!status?.connected}
              ready={ready}
              partial={partial}
            />

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {!status?.connected && (
                <Button
                  size="sm"
                  onClick={() => onboarding.mutate()}
                  disabled={onboarding.isPending}
                >
                  {onboarding.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <>
                      Connect Stripe
                      <ExternalLink className="ml-1 h-3 w-3" />
                    </>
                  )}
                </Button>
              )}

              {partial && (
                <>
                  <Button
                    size="sm"
                    onClick={() => onboarding.mutate()}
                    disabled={onboarding.isPending}
                  >
                    {onboarding.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      "Finish onboarding"
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => refetch()}
                    disabled={isLoading}
                  >
                    Re-check status
                  </Button>
                </>
              )}

              {ready && (
                <>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => dashboard.mutate()}
                    disabled={dashboard.isPending}
                  >
                    {dashboard.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <>
                        Open Stripe Dashboard
                        <ExternalLink className="ml-1 h-3 w-3" />
                      </>
                    )}
                  </Button>
                </>
              )}
            </div>

            {(onboarding.error || dashboard.error) && (
              <p className="mt-2 text-[11px] text-destructive">
                {String(onboarding.error || dashboard.error)}
              </p>
            )}
          </div>
        </div>
      </div>

      <Link
        href="/settings/payouts"
        className="mt-3 inline-flex items-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
      >
        View payment history
        <ArrowRight className="h-3 w-3" />
      </Link>
    </section>
  );
}

function PayoutStatusLabel({
  isLoading,
  connected,
  ready,
  partial,
}: {
  isLoading: boolean;
  connected: boolean;
  ready: boolean;
  partial: boolean;
}) {
  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Checking status…</p>;
  }
  if (ready) {
    return (
      <>
        <p className="text-sm font-medium text-emerald-700 dark:text-emerald-300">
          Ready to receive payouts
        </p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Stripe will send sale proceeds (minus the platform fee) to your bank
          on its standard payout schedule.
        </p>
      </>
    );
  }
  if (partial) {
    return (
      <>
        <p className="text-sm font-medium text-amber-700 dark:text-amber-300">
          Onboarding incomplete
        </p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Stripe still needs additional information to verify your account.
        </p>
      </>
    );
  }
  if (!connected) {
    return (
      <>
        <p className="text-sm font-medium">Not connected</p>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Onboarding takes ~2 minutes — Stripe handles identity, tax forms,
          and bank linking.
        </p>
      </>
    );
  }
  return null;
}
