import { apiClient } from "./client";

export interface AuditLogRow {
  id: string;
  organization_id: string | null;
  workspace_id: string | null;
  actor_user_id: string | null;
  actor_type: "user" | "api_token" | "scim" | "sso" | "system" | string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  data: Record<string, unknown>;
  created_at: string;
}

export interface AuditListParams {
  organization_id?: string;
  workspace_id?: string;
  actor_user_id?: string;
  action?: string;
  action_prefix?: string;
  resource_type?: string;
  resource_id?: string;
  since?: string;
  until?: string;
  limit?: number;
  offset?: number;
}

export const auditService = {
  /** Cross-tenant audit query — moderator+ only. */
  listAdmin: (params?: AuditListParams): Promise<AuditLogRow[]> =>
    apiClient.get<AuditLogRow[]>("/admin/audit", { params }).then((r) => r.data),

  /** Build a CSV-export URL. Hand to <a download> so the browser
   *  handles the streamed response without going through axios. */
  csvUrl: (apiBase: string, params?: AuditListParams): string => {
    const qs = new URLSearchParams();
    qs.set("format", "csv");
    Object.entries(params ?? {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    });
    return `${apiBase}/admin/audit?${qs.toString()}`;
  },

  /** Org-scoped audit query — admin+ in any workspace under the org. */
  listOrg: (orgId: string, params?: AuditListParams): Promise<AuditLogRow[]> =>
    apiClient
      .get<AuditLogRow[]>(`/orgs/${orgId}/audit`, { params })
      .then((r) => r.data),
};
