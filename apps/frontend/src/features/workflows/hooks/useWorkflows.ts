"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { workflowService } from "../services/workflowService";
import type { WorkflowCreateInput, WorkflowSaveInput } from "../types";

export const workflowKeys = {
  all: ["workflows"] as const,
  list: () => [...workflowKeys.all, "list"] as const,
  detail: (id: string) => [...workflowKeys.all, "detail", id] as const,
};

export function useWorkflows() {
  return useQuery({
    queryKey: workflowKeys.list(),
    queryFn: workflowService.list,
  });
}

export function useWorkflow(id: string) {
  return useQuery({
    queryKey: workflowKeys.detail(id),
    queryFn: () => workflowService.getById(id),
    enabled: !!id,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: WorkflowCreateInput) => workflowService.create(data),
    onSuccess: (wf) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.list() });
      router.push(`/workflows/${wf.id}`);
    },
  });
}

export function useSaveWorkflow(id: string) {
  return useMutation({
    mutationFn: (data: WorkflowSaveInput) => workflowService.save(id, data),
  });
}

export function useExecuteWorkflow(id: string) {
  return useMutation({
    mutationFn: (inputData: Record<string, unknown>) =>
      workflowService.execute(id, { input_data: inputData }),
  });
}

export function useDeleteWorkflow() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (id: string) => workflowService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.list() });
      router.push("/workflows");
    },
  });
}
