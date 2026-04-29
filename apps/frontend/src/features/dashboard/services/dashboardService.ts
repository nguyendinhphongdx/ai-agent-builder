import { apiClient } from "@/lib/api/client";

export interface AgentsStats {
  total: number;
  by_status: Record<string, number>;
}

export interface ConversationsStats {
  total: number;
  last_30d: number;
}

export interface MessagesStats {
  total: number;
  last_30d: number;
}

export interface TokensByModel {
  model: string;
  tokens: number;
}

export interface TokensStats {
  total: number;
  by_model: TokensByModel[];
}

export interface CurrencyRevenue {
  currency: string;
  gross_cents: number;
  fees_cents: number;
  net_cents: number;
  count: number;
}

export interface RevenueSummary {
  by_currency: CurrencyRevenue[];
  total_paid: number;
  total_refunded: number;
}

export interface DashboardResponse {
  agents: AgentsStats;
  conversations: ConversationsStats;
  messages: MessagesStats;
  tokens: TokensStats;
  revenue: RevenueSummary;
}

export const dashboardService = {
  get: () =>
    apiClient.get<DashboardResponse>("/me/dashboard").then((r) => r.data),
};
