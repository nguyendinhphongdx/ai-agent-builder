import { apiClient } from "./client";

export type WorkspaceRole = "viewer" | "editor" | "admin" | "owner";

export interface PermissionCatalogue {
  permissions: string[];
  builtin_roles: Record<string, string[]>;
}

export interface CustomRole {
  id: string;
  organization_id: string;
  slug: string;
  name: string;
  description: string | null;
  permissions: string[];
  created_at: string;
  updated_at: string;
}

export interface CustomRoleInput {
  slug: string;
  name: string;
  description?: string | null;
  permissions: string[];
}

export interface CustomRolePatch {
  name?: string;
  description?: string | null;
  permissions?: string[];
}

export const permissionsService = {
  catalogue: (): Promise<PermissionCatalogue> =>
    apiClient.get<PermissionCatalogue>("/permissions").then((r) => r.data),

  listCustom: (orgId: string): Promise<CustomRole[]> =>
    apiClient
      .get<CustomRole[]>(`/orgs/${orgId}/custom-roles`)
      .then((r) => r.data),

  createCustom: (orgId: string, body: CustomRoleInput): Promise<CustomRole> =>
    apiClient
      .post<CustomRole>(`/orgs/${orgId}/custom-roles`, body)
      .then((r) => r.data),

  updateCustom: (
    orgId: string,
    roleId: string,
    body: CustomRolePatch,
  ): Promise<CustomRole> =>
    apiClient
      .patch<CustomRole>(`/orgs/${orgId}/custom-roles/${roleId}`, body)
      .then((r) => r.data),

  deleteCustom: (orgId: string, roleId: string): Promise<void> =>
    apiClient
      .delete(`/orgs/${orgId}/custom-roles/${roleId}`)
      .then(() => undefined),
};
