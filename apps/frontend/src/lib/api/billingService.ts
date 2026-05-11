import { apiClient } from "./client";

export interface PlanInfo {
  code: string;
  name: string;
  monthly_llm_tokens: number;
  monthly_kb_queries: number;
  max_workspaces: number;
  max_members: number;
  features: Record<string, boolean | number>;
  is_self_serve: boolean;
}

export interface SubscriptionInfo {
  plan: PlanInfo;
  status: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  has_stripe_subscription: boolean;
}

export interface QuotaUsage {
  used: number;
  limit: number;
  pct: number;
}

export interface BillingOverview {
  subscription: SubscriptionInfo;
  tokens: QuotaUsage;
  kb_queries: QuotaUsage;
}

export interface CheckoutSessionInfo {
  url: string;
}

export interface PortalSessionInfo {
  url: string;
}

export const billingService = {
  listPlans: (): Promise<PlanInfo[]> =>
    apiClient.get<PlanInfo[]>("/billing/plans").then((r) => r.data),

  getSubscription: (): Promise<BillingOverview> =>
    apiClient.get<BillingOverview>("/billing/subscription").then((r) => r.data),

  checkout: (planCode: string): Promise<CheckoutSessionInfo> =>
    apiClient
      .post<CheckoutSessionInfo>("/billing/checkout", { plan_code: planCode })
      .then((r) => r.data),

  portal: (): Promise<PortalSessionInfo> =>
    apiClient
      .post<PortalSessionInfo>("/billing/portal", {})
      .then((r) => r.data),
};
