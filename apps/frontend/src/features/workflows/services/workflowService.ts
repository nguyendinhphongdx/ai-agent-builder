import { apiClient } from "@/lib/api/client";
import type { Workflow, WorkflowDetail, WorkflowCreateInput, WorkflowSaveInput } from "../types";

export const workflowService = {
  list: () =>
    apiClient.get<Workflow[]>("/workflows").then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<WorkflowDetail>(`/workflows/${id}`).then((r) => r.data),

  create: (data: WorkflowCreateInput) =>
    apiClient.post<Workflow>("/workflows", data).then((r) => r.data),

  save: (id: string, data: WorkflowSaveInput) =>
    apiClient.put<WorkflowDetail>(`/workflows/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/workflows/${id}`),

  execute: (id: string, input: Record<string, unknown>) =>
    apiClient.post(`/workflows/${id}/execute`, input).then((r) => r.data),

  listRuns: (id: string, limit = 20) =>
    apiClient.get(`/workflows/${id}/runs`, { params: { limit } }).then((r) => r.data),

  getRun: (workflowId: string, runId: string) =>
    apiClient.get(`/workflows/${workflowId}/runs/${runId}`).then((r) => r.data),
};
