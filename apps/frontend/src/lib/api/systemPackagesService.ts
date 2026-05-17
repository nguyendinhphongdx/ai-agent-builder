import { apiClient } from "./client";

/**
 * Read-only PLANS catalogue — mirrors ``/api/system/packages``.
 * Edits to a plan happen in code (``plans.py``); this surface is
 * just for visibility into what tiers exist + how many orgs use each.
 */

export interface SystemPackageRow {
  code: string;
  name: string;
  monthly_llm_tokens: number;   // 0 = unlimited
  monthly_kb_queries: number;
  max_workspaces: number;
  max_members: number;
  features: Record<string, boolean | number>;
  stripe_price_id: string | null;
  stripe_metered_price_id: string | null;
  is_self_serve: boolean;
  active_orgs: number;
}

export const systemPackagesService = {
  list: (): Promise<SystemPackageRow[]> =>
    apiClient
      .get<SystemPackageRow[]>("/system/packages")
      .then((r) => r.data),
};
