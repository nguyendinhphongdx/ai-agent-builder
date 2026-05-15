import { apiClient } from "./client";
import type {
  InvitationAcceptResponse,
  InvitationCreateInput,
  WorkspaceCreateInput,
  WorkspaceInvitation,
  WorkspaceMember,
  WorkspaceRole,
  WorkspaceSummary,
  WorkspaceUpdateInput,
} from "@/features/workspaces/types";

export const workspaceService = {
  list: (): Promise<WorkspaceSummary[]> =>
    apiClient.get<WorkspaceSummary[]>("/workspaces").then((r) => r.data),

  create: (body: WorkspaceCreateInput): Promise<WorkspaceSummary> =>
    apiClient.post<WorkspaceSummary>("/workspaces", body).then((r) => r.data),

  get: (id: string): Promise<WorkspaceSummary> =>
    apiClient.get<WorkspaceSummary>(`/workspaces/${id}`).then((r) => r.data),

  update: (id: string, body: WorkspaceUpdateInput): Promise<WorkspaceSummary> =>
    apiClient.patch<WorkspaceSummary>(`/workspaces/${id}`, body).then((r) => r.data),

  delete: (id: string): Promise<void> =>
    apiClient.delete(`/workspaces/${id}`).then(() => undefined),

  // ── Members
  listMembers: (id: string): Promise<WorkspaceMember[]> =>
    apiClient.get<WorkspaceMember[]>(`/workspaces/${id}/members`).then((r) => r.data),

  /** Org members not yet in this workspace — feeds the "Add member"
   *  picker. New-to-the-platform invites happen at /org/members. */
  listAddableMembers: (
    id: string,
  ): Promise<
    Array<{
      user_id: string;
      email: string;
      full_name: string | null;
      org_role: string;
    }>
  > =>
    apiClient
      .get<
        Array<{
          user_id: string;
          email: string;
          full_name: string | null;
          org_role: string;
        }>
      >(`/workspaces/${id}/addable-members`)
      .then((r) => r.data),

  addMember: (
    id: string,
    body: { user_id: string; role: WorkspaceRole },
  ): Promise<WorkspaceMember> =>
    apiClient
      .post<WorkspaceMember>(`/workspaces/${id}/members`, body)
      .then((r) => r.data),

  updateMember: (
    id: string,
    userId: string,
    role: WorkspaceRole,
  ): Promise<WorkspaceMember> =>
    apiClient
      .patch<WorkspaceMember>(`/workspaces/${id}/members/${userId}`, { role })
      .then((r) => r.data),

  removeMember: (id: string, userId: string): Promise<void> =>
    apiClient
      .delete(`/workspaces/${id}/members/${userId}`)
      .then(() => undefined),

  // ── Invitations
  listInvitations: (id: string): Promise<WorkspaceInvitation[]> =>
    apiClient
      .get<WorkspaceInvitation[]>(`/workspaces/${id}/invitations`)
      .then((r) => r.data),

  createInvitation: (
    id: string,
    body: InvitationCreateInput,
  ): Promise<WorkspaceInvitation> =>
    apiClient
      .post<WorkspaceInvitation>(`/workspaces/${id}/invitations`, body)
      .then((r) => r.data),

  revokeInvitation: (id: string, invId: string): Promise<void> =>
    apiClient
      .delete(`/workspaces/${id}/invitations/${invId}`)
      .then(() => undefined),

  // ── Public-by-token accept (still requires auth)
  acceptInvitation: (token: string): Promise<InvitationAcceptResponse> =>
    apiClient
      .post<InvitationAcceptResponse>(`/workspaces/invitations/${token}/accept`)
      .then((r) => r.data),
};
