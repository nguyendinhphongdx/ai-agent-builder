import { apiClient } from "./client";

/**
 * Platform-admin dashboard — mirrors ``/api/system/dashboard``.
 *
 * Single endpoint returning every KPI the system org needs to see
 * at a glance. Numbers are estimates (MRR derived from plan tier x
 * live-sub count, not real Stripe invoices); the dashboard is for
 * operational visibility, not accounting.
 */

export interface SystemDashboard {
  as_of: string;
  orgs: {
    total: number;
    new_30d: number;
    new_7d: number;
    by_plan: Record<string, number>;
  };
  users: {
    total: number;
    active_30d: number;
    active_7d: number;
    activity_rate_pct: number;
  };
  subscriptions: {
    live: number;
    cancel_scheduled: number;
  };
  revenue: {
    mrr_usd_cents: number;
    hub_total_cents: number;
    hub_total_purchases: number;
    hub_30d_cents: number;
    hub_30d_purchases: number;
  };
  usage_30d: {
    tokens: number;
    kb_queries: number;
    conversations: number;
  };
  resources: {
    workspaces: number;
    agents: number;
  };
  top_orgs_by_tokens_30d: Array<{
    id: string;
    name: string;
    slug: string;
    plan: string;
    tokens: number;
  }>;
  contracts: {
    available: boolean;
    signed: number;
    active: number;
    expiring_30d: number;
    total_value_cents: number;
  };
}

export const systemDashboardService = {
  get: (): Promise<SystemDashboard> =>
    apiClient.get<SystemDashboard>("/system/dashboard").then((r) => r.data),
};
