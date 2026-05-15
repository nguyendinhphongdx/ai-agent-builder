"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useWorkspacePath } from "@/features/workspaces";
import { agentService } from "../services/agentService";
import type { AgentCreateInput, AgentUpdateInput } from "../types";

export const agentKeys = {
  all: ["agents"] as const,
  list: () => [...agentKeys.all, "list"] as const,
  detail: (id: string) => [...agentKeys.all, "detail", id] as const,
};

export function useAgents() {
  return useQuery({
    queryKey: agentKeys.list(),
    queryFn: agentService.list,
  });
}

export function useAgent(id: string) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => agentService.getById(id),
    enabled: !!id,
  });
}

export function useCreateAgent() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const wp = useWorkspacePath();

  return useMutation({
    mutationFn: (data: AgentCreateInput) => agentService.create(data),
    onSuccess: (agent) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.list() });
      router.push(wp(`/agents/${agent.id}`));
    },
  });
}

export function useUpdateAgent(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AgentUpdateInput) => agentService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: agentKeys.list() });
    },
  });
}

export function useDeleteAgent() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const wp = useWorkspacePath();

  return useMutation({
    mutationFn: (id: string) => agentService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.list() });
      router.push(wp("/agents"));
    },
  });
}
