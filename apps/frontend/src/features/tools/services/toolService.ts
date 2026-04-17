import { apiClient } from "@/lib/api/client";
import type { Tool, ToolCreateInput, ToolUpdateInput, ToolTestResult } from "../types";

export const toolService = {
  list: () =>
    apiClient.get<Tool[]>("/tools").then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<Tool>(`/tools/${id}`).then((r) => r.data),

  create: (data: ToolCreateInput) =>
    apiClient.post<Tool>("/tools", data).then((r) => r.data),

  update: (id: string, data: ToolUpdateInput) =>
    apiClient.put<Tool>(`/tools/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/tools/${id}`),

  test: (id: string, inputData: Record<string, unknown>) =>
    apiClient
      .post<ToolTestResult>(`/tools/${id}/test`, { input_data: inputData })
      .then((r) => r.data),
};
