import { apiClient } from "./client";

export interface UsageTotals {
  count: number;
  tokens: number;
  cost_usd: number;
  avg_latency_ms: number;
  since: string;
  until: string;
}

export interface UsageDailyPoint {
  day: string;
  count: number;
  tokens: number;
  cost_usd: number;
}

export interface UsageModelRow {
  provider: string | null;
  model: string | null;
  count: number;
  tokens: number;
  cost_usd: number;
}

export interface UsageQueryParams {
  since?: string;
  until?: string;
}

export const usageService = {
  totals: (params?: UsageQueryParams): Promise<UsageTotals> =>
    apiClient
      .get<UsageTotals>("/usage/totals", { params })
      .then((r) => r.data),

  daily: (params?: UsageQueryParams): Promise<UsageDailyPoint[]> =>
    apiClient
      .get<UsageDailyPoint[]>("/usage/daily", { params })
      .then((r) => r.data),

  byModel: (params?: UsageQueryParams): Promise<UsageModelRow[]> =>
    apiClient
      .get<UsageModelRow[]>("/usage/by-model", { params })
      .then((r) => r.data),
};
