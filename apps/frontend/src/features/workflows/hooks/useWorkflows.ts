"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useWorkspacePath } from "@/features/workspaces";
import { workflowService } from "../services/workflowService";
import type {
  WorkflowCreateInput,
  WorkflowSaveInput,
  WorkflowExecuteInput,
  WorkflowRun,
  NodeExecuteInput,
} from "../types";

export const workflowKeys = {
  all: ["workflows"] as const,
  list: () => [...workflowKeys.all, "list"] as const,
  detail: (id: string) => [...workflowKeys.all, "detail", id] as const,
  runs: (id: string) => [...workflowKeys.all, "runs", id] as const,
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
  const wp = useWorkspacePath();

  return useMutation({
    mutationFn: (data: WorkflowCreateInput) => workflowService.create(data),
    onSuccess: (wf) => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.list() });
      router.push(wp(`/workflows/${wf.id}`));
    },
  });
}

export function useSaveWorkflow(id: string) {
  return useMutation({
    mutationFn: (data: WorkflowSaveInput) => workflowService.save(id, data),
  });
}

export function useExecuteWorkflow(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (input: WorkflowExecuteInput) => workflowService.execute(id, input),
    onSuccess: (run) => {
      // Prepend the new run so any consumer of `runs(id)` sees it immediately.
      queryClient.setQueryData<WorkflowRun[]>(workflowKeys.runs(id), (prev) =>
        prev ? [run, ...prev] : [run],
      );
    },
  });
}

/**
 * Execute a single node — NDV "Execute step". Result is persisted as a
 * partial run; we prepend it to the same `runs` cache so the NDV picks up
 * fresh input/output without an extra fetch.
 */
export function useExecuteNode(workflowId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ nodeId, input }: { nodeId: string; input: NodeExecuteInput }) =>
      workflowService.executeNode(workflowId, nodeId, input),
    onSuccess: (run) => {
      queryClient.setQueryData<WorkflowRun[]>(workflowKeys.runs(workflowId), (prev) =>
        prev ? [run, ...prev] : [run],
      );
    },
  });
}

/**
 * Source of truth for run history. Latest run = `data[0]`.
 *
 * Polls every 1.5s while the latest run is still `running` so streaming
 * node executions show up in the NDV without a manual refresh.
 */
export function useWorkflowRuns(id: string, limit = 20) {
  return useQuery({
    queryKey: workflowKeys.runs(id),
    queryFn: () => workflowService.listRuns(id, limit),
    enabled: !!id,
    staleTime: 30_000,
    refetchInterval: (query) =>
      query.state.data?.[0]?.status === "running" ? 1500 : false,
  });
}

/**
 * Rotate the workflow's webhook token. The previous URL stops working
 * immediately — caller should warn the user before invoking.
 */
export function useRotateWebhookToken(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => workflowService.rotateWebhookToken(id),
    onSuccess: (workflow) => {
      queryClient.setQueryData(workflowKeys.detail(id), workflow);
    },
  });
}

export function useDeleteWorkflow() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const wp = useWorkspacePath();

  return useMutation({
    mutationFn: (id: string) => workflowService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: workflowKeys.list() });
      router.push(wp("/workflows"));
    },
  });
}
