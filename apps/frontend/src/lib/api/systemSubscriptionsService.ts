import { apiClient } from "./client";

/**
 * Platform-admin subscriptions surface — mirrors
 * ``/api/system/subscriptions``. Server enforces system-org admin
 * membership; FE pages also gate via ``useSystemAccess``.
 */

export interface SystemSubscriptionRow {
  org_id: string;
  org_name: string;
  org_slug: string;
  plan_code: string;
  /** "active" | "trialing" | "past_due" | "canceled" | "incomplete" | "unpaid" | "none" */
  status: string;
  is_live: boolean;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  stripe_subscription_id: string | null;
  created_at: string;
}

export interface SystemSubscriptionsList {
  rows: SystemSubscriptionRow[];
  total: number;
}

export interface SystemSubscriptionStats {
  total_orgs: number;
  live_subs: number;
  by_status: Record<string, number>;
  by_plan: Record<string, number>;
  trialing: number;
  cancel_scheduled: number;
}

export interface SubscriptionListParams {
  status?: string;
  plan?: string;
  limit?: number;
  offset?: number;
}

export const systemSubscriptionsService = {
  list: (params?: SubscriptionListParams): Promise<SystemSubscriptionsList> =>
    apiClient
      .get<SystemSubscriptionsList>("/system/subscriptions", { params })
      .then((r) => r.data),

  stats: (): Promise<SystemSubscriptionStats> =>
    apiClient
      .get<SystemSubscriptionStats>("/system/subscriptions/stats")
      .then((r) => r.data),

  get: (orgId: string): Promise<SystemSubscriptionRow> =>
    apiClient
      .get<SystemSubscriptionRow>(`/system/subscriptions/${orgId}`)
      .then((r) => r.data),

  setPlan: (orgId: string, planCode: string): Promise<SystemSubscriptionRow> =>
    apiClient
      .post<SystemSubscriptionRow>(`/system/subscriptions/${orgId}/set-plan`, {
        plan_code: planCode,
      })
      .then((r) => r.data),

  cancel: (
    orgId: string,
    options?: { immediate?: boolean },
  ): Promise<SystemSubscriptionRow> =>
    apiClient
      .post<SystemSubscriptionRow>(`/system/subscriptions/${orgId}/cancel`, {
        immediate: options?.immediate ?? false,
      })
      .then((r) => r.data),
};
