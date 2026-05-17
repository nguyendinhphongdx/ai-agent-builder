import { apiClient } from "./client";

/**
 * Platform-owner admin surface — mirrors ``/api/system/*`` (see
 * apps/backend/app/modules/api/system/router.py).
 *
 * Every call requires the caller to be an owner/admin of the org with
 * ``is_system=true``. The BE returns 403 otherwise; the UI should
 * gate route entry on the same check so users never see a denied
 * screen.
 */

export interface SystemOrgRow {
  id: string;
  name: string;
  slug: string;
  plan: string;
  billing_email: string | null;
  is_system: boolean;
  member_count: number;
  workspace_count: number;
  created_at: string;
}

export interface SystemOrgDetail extends SystemOrgRow {
  settings: Record<string, unknown>;
  owner_email: string | null;
}

export interface SystemOrgListResponse {
  rows: SystemOrgRow[];
  total: number;
}

export interface SystemOrgCreateInput {
  name: string;
  slug: string;
  owner_email: string;
  billing_email?: string | null;
  plan?: string | null;
}

export interface SystemOrgPatchInput {
  name?: string;
  plan?: string;
  billing_email?: string | null;
  settings?: Record<string, unknown>;
}

export const systemService = {
  listOrganizations: (params?: {
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<SystemOrgListResponse> =>
    apiClient
      .get<SystemOrgListResponse>("/system/organizations", { params })
      .then((r) => r.data),

  getOrganization: (orgId: string): Promise<SystemOrgDetail> =>
    apiClient
      .get<SystemOrgDetail>(`/system/organizations/${orgId}`)
      .then((r) => r.data),

  createOrganization: (body: SystemOrgCreateInput): Promise<SystemOrgDetail> =>
    apiClient
      .post<SystemOrgDetail>("/system/organizations", body)
      .then((r) => r.data),

  updateOrganization: (
    orgId: string,
    body: SystemOrgPatchInput,
  ): Promise<SystemOrgDetail> =>
    apiClient
      .patch<SystemOrgDetail>(`/system/organizations/${orgId}`, body)
      .then((r) => r.data),

  deleteOrganization: (orgId: string): Promise<void> =>
    apiClient
      .delete(`/system/organizations/${orgId}`)
      .then(() => undefined),
};
