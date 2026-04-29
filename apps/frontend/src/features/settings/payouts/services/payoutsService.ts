import { apiClient } from "@/lib/api/client";

export interface PayoutStatus {
  connected: boolean;
  charges_enabled: boolean;
  payouts_enabled: boolean;
  account_id: string | null;
}

export interface PayoutHistoryItem {
  id: string;
  template_id: string;
  template_title: string;
  buyer_email_masked: string | null;
  price_paid_cents: number;
  currency: string;
  platform_fee_cents: number;
  net_cents: number;
  provider: "stripe" | "momo";
  status: "paid" | "refunded" | "pending" | "failed";
  purchased_at: string;
  refunded_at: string | null;
  /** Author-side settlement. Stripe rows: stamped at payment via Connect.
   *  MoMo rows: stays null until ops marks the manual transfer. */
  settled_at: string | null;
}

export interface PayoutHistoryResponse {
  items: PayoutHistoryItem[];
  total: number;
  has_more: boolean;
}

export interface PayoutMonthlyRow {
  month: string; // "YYYY-MM"
  currency: string;
  gross_cents: number;
  fees_cents: number;
  net_cents: number;
  count: number;
}

export interface PayoutCurrencyTotal {
  currency: string;
  gross_cents: number;
  fees_cents: number;
  net_cents: number;
  count: number;
}

export interface PayoutSummary {
  by_month: PayoutMonthlyRow[];
  totals: PayoutCurrencyTotal[];
}

export interface HistoryParams {
  status?: "paid" | "refunded";
  provider?: "stripe" | "momo";
  limit?: number;
  offset?: number;
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

  history: (params: HistoryParams = {}) =>
    apiClient
      .get<PayoutHistoryResponse>("/me/payouts/history", { params })
      .then((r) => r.data),

  summary: () =>
    apiClient.get<PayoutSummary>("/me/payouts/summary").then((r) => r.data),
};
