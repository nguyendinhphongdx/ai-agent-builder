/** Shapes mirror the backend pydantic models in app/workspaces/schemas.py. */

export type WorkspaceRole = "viewer" | "editor" | "admin" | "owner";

export interface OrganizationRef {
  id: string;
  name: string;
  slug: string;
  plan: string;
}

export interface WorkspaceSummary {
  id: string;
  name: string;
  slug: string;
  is_personal: boolean;
  organization: OrganizationRef;
  settings: Record<string, unknown>;
  role: WorkspaceRole;
  created_at: string;
}

export interface WorkspaceCreateInput {
  name: string;
  slug?: string;
  organization_id?: string;
}

export interface WorkspaceUpdateInput {
  name?: string;
  slug?: string;
  settings?: Record<string, unknown>;
}

export interface WorkspaceMemberUser {
  id: string;
  email: string;
  full_name: string | null;
}

export interface WorkspaceMember {
  workspace_id: string;
  user_id: string;
  role: WorkspaceRole;
  joined_at: string;
  user: WorkspaceMemberUser;
}

export interface WorkspaceInvitation {
  id: string;
  workspace_id: string;
  email: string;
  role: WorkspaceRole;
  token: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
}

export interface InvitationCreateInput {
  email: string;
  role: WorkspaceRole;
}

export interface InvitationAcceptResponse {
  workspace: WorkspaceSummary;
}

/** Role rank used for permission-aware UI gating in the FE. Mirrors
 *  the backend rank in app/workspaces/permissions.py. */
export const ROLE_RANK: Record<WorkspaceRole, number> = {
  viewer: 0,
  editor: 1,
  admin: 2,
  owner: 3,
};

export function roleAtLeast(role: WorkspaceRole, min: WorkspaceRole): boolean {
  return ROLE_RANK[role] >= ROLE_RANK[min];
}
