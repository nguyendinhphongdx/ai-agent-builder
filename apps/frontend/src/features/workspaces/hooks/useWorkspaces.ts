"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workspaceService } from "@/lib/api/workspaceService";
import type {
  InvitationCreateInput,
  WorkspaceCreateInput,
  WorkspaceRole,
  WorkspaceUpdateInput,
} from "../types";

export const workspaceKeys = {
  all: ["workspaces"] as const,
  list: () => [...workspaceKeys.all, "list"] as const,
  detail: (id: string) => [...workspaceKeys.all, "detail", id] as const,
  members: (id: string) => [...workspaceKeys.all, id, "members"] as const,
  invitations: (id: string) => [...workspaceKeys.all, id, "invitations"] as const,
};

/** List workspaces the caller is a member of.
 *
 *  After Phase 3 of the Hub refactor there's no "current workspace"
 *  client-side state — the access_token cookie carries the
 *  workspace claim, and consumers that need "which workspace am I
 *  in" call ``useSession()`` instead. This hook is just the list.
 */
export function useWorkspaces() {
  return useQuery({
    queryKey: workspaceKeys.list(),
    queryFn: workspaceService.list,
  });
}

export function useWorkspace(id: string | null) {
  return useQuery({
    queryKey: workspaceKeys.detail(id ?? ""),
    queryFn: () => workspaceService.get(id!),
    enabled: !!id,
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkspaceCreateInput) => workspaceService.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceKeys.list() });
      // Caller decides whether to enter the new workspace (via
      // ``sessionService.enter``) — usually the Hub's create dialog
      // does, but a "create then come back later" flow shouldn't be
      // forced into the new tenant.
    },
  });
}

export function useUpdateWorkspace(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkspaceUpdateInput) => workspaceService.update(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceKeys.list() });
      qc.invalidateQueries({ queryKey: workspaceKeys.detail(id) });
    },
  });
}

export function useDeleteWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => workspaceService.delete(id),
    onSuccess: () => {
      // The deleted workspace's token is invalidated server-side
      // (workspace cascade-deletes the membership row); next API
      // call returns 401 and the FE bounces to /org.
      qc.invalidateQueries({ queryKey: workspaceKeys.list() });
    },
  });
}

// ── Members
export function useWorkspaceMembers(id: string | null) {
  return useQuery({
    queryKey: workspaceKeys.members(id ?? ""),
    queryFn: () => workspaceService.listMembers(id!),
    enabled: !!id,
  });
}

export function useAddableWorkspaceMembers(id: string | null) {
  return useQuery({
    queryKey: [...workspaceKeys.members(id ?? ""), "addable"],
    queryFn: () => workspaceService.listAddableMembers(id!),
    enabled: !!id,
  });
}

export function useAddWorkspaceMember(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { user_id: string; role: WorkspaceRole }) =>
      workspaceService.addMember(workspaceId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceKeys.members(workspaceId) });
    },
  });
}

export function useUpdateMemberRole(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: WorkspaceRole }) =>
      workspaceService.updateMember(workspaceId, userId, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceKeys.members(workspaceId) });
    },
  });
}

export function useRemoveMember(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => workspaceService.removeMember(workspaceId, userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceKeys.members(workspaceId) });
      qc.invalidateQueries({ queryKey: workspaceKeys.list() });
    },
  });
}

// ── Invitations
export function useWorkspaceInvitations(id: string | null) {
  return useQuery({
    queryKey: workspaceKeys.invitations(id ?? ""),
    queryFn: () => workspaceService.listInvitations(id!),
    enabled: !!id,
  });
}

export function useCreateInvitation(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: InvitationCreateInput) =>
      workspaceService.createInvitation(workspaceId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceKeys.invitations(workspaceId) });
    },
  });
}

export function useRevokeInvitation(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invId: string) =>
      workspaceService.revokeInvitation(workspaceId, invId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workspaceKeys.invitations(workspaceId) });
    },
  });
}

export function useAcceptInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => workspaceService.acceptInvitation(token),
    onSuccess: () => {
      // Caller routes to /org so the user picks (and explicitly
      // enters via sessionService.enter) the newly-joined workspace.
      // Auto-entering bypasses the enter-workspace audit trail and
      // gives a confusing UX if the invite landed in a different
      // tenant than the one they were just using.
      qc.invalidateQueries({ queryKey: workspaceKeys.list() });
    },
  });
}
