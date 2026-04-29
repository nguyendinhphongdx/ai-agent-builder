import { apiClient } from "@/lib/api/client";
import type {
  Workflow,
  WorkflowDetail,
  WorkflowCreateInput,
  WorkflowSaveInput,
  WorkflowExecuteInput,
  WorkflowRun,
  NodeExecuteInput,
} from "../types";

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

  execute: (id: string, input: WorkflowExecuteInput) =>
    apiClient.post<WorkflowRun>(`/workflows/${id}/execute`, input).then((r) => r.data),

  executeNode: (workflowId: string, nodeId: string, input: NodeExecuteInput) =>
    apiClient
      .post<WorkflowRun>(`/workflows/${workflowId}/nodes/${nodeId}/execute`, input)
      .then((r) => r.data),

  rotateWebhookToken: (id: string) =>
    apiClient
      .post<WorkflowDetail>(`/workflows/${id}/webhook-token/rotate`)
      .then((r) => r.data),

  listRuns: (id: string, limit = 20) =>
    apiClient.get<WorkflowRun[]>(`/workflows/${id}/runs`, { params: { limit } }).then((r) => r.data),

  getRun: (workflowId: string, runId: string) =>
    apiClient.get<WorkflowRun>(`/workflows/${workflowId}/runs/${runId}`).then((r) => r.data),
};
