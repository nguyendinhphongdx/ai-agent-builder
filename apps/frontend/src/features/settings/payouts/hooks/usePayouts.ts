"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { payoutsService } from "../services/payoutsService";

export const payoutsKeys = {
  status: () => ["payouts", "status"] as const,
};

/** Cached onboarding status. The backend mirrors Stripe's webhook so this
 *  is fresh enough for the Settings UI without polling. */
export function usePayoutStatus() {
  return useQuery({
    queryKey: payoutsKeys.status(),
    queryFn: payoutsService.status,
    staleTime: 30_000,
  });
}

/** Mints a fresh single-use Stripe AccountLink and opens Stripe-hosted
 *  onboarding in a new tab. AccountLinks expire fast — always re-mint. */
export function useStartOnboarding() {
  return useMutation({
    mutationFn: payoutsService.startOnboarding,
    onSuccess: (url) => {
      window.open(url, "_blank", "noopener,noreferrer");
    },
  });
}

/** Opens the author's Stripe Express dashboard (payouts, taxes, disputes). */
export function useDashboardLink() {
  return useMutation({
    mutationFn: payoutsService.dashboardLink,
    onSuccess: (url) => {
      window.open(url, "_blank", "noopener,noreferrer");
    },
  });
}
