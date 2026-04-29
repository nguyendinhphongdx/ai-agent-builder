"use client";

import { Banknote, ExternalLink, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SettingsCard } from "@/features/settings/components/SettingsPrimitives";
import {
  useDashboardLink,
  usePayoutStatus,
  useStartOnboarding,
} from "../hooks/usePayouts";

/** Stripe Connect onboarding panel. Composes a SettingsCard so it stacks
 *  cleanly with the rest of the Payouts page sections. */
export function PayoutsSection() {
  const { data: status, isLoading, refetch } = usePayoutStatus();
  const onboarding = useStartOnboarding();
  const dashboard = useDashboardLink();

  const ready = !!status?.charges_enabled && !!status?.payouts_enabled;
  const partial = !!status?.connected && !ready;

  return (
    <SettingsCard
      title="Stripe Connect"
      description="Required to receive USD/EUR/GBP sales. Free templates don't need this."
    >
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
          <Banknote className="h-4 w-4 text-muted-foreground" />
        </div>

        <div className="min-w-0 flex-1">
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
            )}
          </div>

          {(onboarding.error || dashboard.error) && (
            <p className="mt-2 text-[11px] text-destructive">
              {String(onboarding.error || dashboard.error)}
            </p>
          )}
        </div>
      </div>
    </SettingsCard>
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
          Stripe sends sale proceeds (minus the platform fee) to your bank on
          its standard payout schedule.
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
