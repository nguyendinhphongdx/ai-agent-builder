import { apiClient } from "@/lib/api/client";

export interface PayoutStatus {
  connected: boolean;
  charges_enabled: boolean;
  payouts_enabled: boolean;
  account_id: string | null;
}

export const payoutsService = {
  status: () =>
    apiClient.get<PayoutStatus>("/me/payouts/status").then((r) => r.data),

  startOnboarding: () =>
    apiClient
      .post<{ url: string }>("/me/payouts/onboarding-link")
      .then((r) => r.data.url),

  dashboardLink: () =>
    apiClient
      .post<{ url: string }>("/me/payouts/dashboard-link")
      .then((r) => r.data.url),
};
