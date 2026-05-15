import { apiClient } from "./client";

/**
 * Organization API client — mirrors ``/api/organizations`` (see
 * apps/backend/app/modules/identity/organizations/router.py).
 *
 * The Hub UI is the main consumer; per-workspace pages stay on the
 * /workspaces API. This file ships only what the Hub needs in Phase 1
 * — list orgs + list workspaces under one org. Members / billing /
 * settings calls land with the Phase 4 features.
 */

export type OrgRole = "owner" | "admin" | "editor" | "viewer";

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
  plan: string;
  role: OrgRole;
  billing_email: string | null;
  created_at: string;
}

export interface OrganizationWorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  is_personal: boolean;
  monthly_token_quota_override: number | null;
  monthly_kb_query_quota_override: number | null;
  force_mfa: boolean;
  member_count: number;
  created_at: string | null;
}

export const organizationsService = {
  /** Orgs the caller belongs to. */
  list: (): Promise<OrganizationSummary[]> =>
    apiClient.get<OrganizationSummary[]>("/organizations").then((r) => r.data),

  get: (orgId: string): Promise<OrganizationSummary> =>
    apiClient
      .get<OrganizationSummary>(`/organizations/${orgId}`)
      .then((r) => r.data),

  /** Every workspace under one org — even ones the caller hasn't
   *  joined. Used by the Hub's Workspaces tab so an org-admin can
   *  manage workspaces they aren't a direct member of. */
  listWorkspaces: (orgId: string): Promise<OrganizationWorkspaceSummary[]> =>
    apiClient
      .get<OrganizationWorkspaceSummary[]>(`/organizations/${orgId}/workspaces`)
      .then((r) => r.data),
};
