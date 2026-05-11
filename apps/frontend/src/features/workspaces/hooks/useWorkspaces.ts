"use client";

import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { workspaceService } from "@/lib/api/workspaceService";
import { useWorkspaceStore } from "../stores/workspaceStore";
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
 *  Side effect: on first successful load, if the persisted
 *  ``currentWorkspaceId`` doesn't match any returned workspace (deleted
 *  / removed from membership / never set), reset it to the first
 *  personal workspace in the list.
 */
export function useWorkspaces() {
  const setCurrent = useWorkspaceStore((s) => s.setCurrentWorkspaceId);
  const currentId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const query = useQuery({
    queryKey: workspaceKeys.list(),
    queryFn: workspaceService.list,
  });

  useEffect(() => {
    if (!query.data) return;
    const ids = new Set(query.data.map((w) => w.id));
    if (!currentId || !ids.has(currentId)) {
      const personal = query.data.find((w) => w.is_personal) ?? query.data[0];
      if (personal) setCurrent(personal.id);
    }
  }, [query.data, currentId, setCurrent]);

  return query;
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
  const setCurrent = useWorkspaceStore((s) => s.setCurrentWorkspaceId);
  return useMutation({
    mutationFn: (body: WorkspaceCreateInput) => workspaceService.create(body),
    onSuccess: (ws) => {
      qc.invalidateQueries({ queryKey: workspaceKeys.list() });
      // Switch into the just-created workspace — that's almost always
      // what the user wants right after clicking "Create".
      setCurrent(ws.id);
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
  const setCurrent = useWorkspaceStore((s) => s.setCurrentWorkspaceId);
  const currentId = useWorkspaceStore((s) => s.currentWorkspaceId);
  return useMutation({
    mutationFn: (id: string) => workspaceService.delete(id),
    onSuccess: (_void, deletedId) => {
      if (currentId === deletedId) setCurrent(null);
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
  const setCurrent = useWorkspaceStore((s) => s.setCurrentWorkspaceId);
  return useMutation({
    mutationFn: (token: string) => workspaceService.acceptInvitation(token),
    onSuccess: (res) => {
      // Drop the user straight into the newly-joined workspace.
      setCurrent(res.workspace.id);
      qc.invalidateQueries({ queryKey: workspaceKeys.list() });
    },
  });
}
