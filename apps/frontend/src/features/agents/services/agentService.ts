import { apiClient } from "@/lib/api/client";
import type { Agent, AgentCreateInput, AgentListItem, AgentUpdateInput } from "../types";

export const agentService = {
  list: () =>
    apiClient.get<AgentListItem[]>("/agents").then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<Agent>(`/agents/${id}`).then((r) => r.data),

  create: (data: AgentCreateInput) =>
    apiClient.post<Agent>("/agents", data).then((r) => r.data),

  update: (id: string, data: AgentUpdateInput) =>
    apiClient.put<Agent>(`/agents/${id}`, data).then((r) => r.data),

  delete: (id: string) => apiClient.delete(`/agents/${id}`),

  attachTool: (agentId: string, toolId: string) =>
    apiClient.post(`/agents/${agentId}/tools/${toolId}`),

  detachTool: (agentId: string, toolId: string) =>
    apiClient.delete(`/agents/${agentId}/tools/${toolId}`),

  attachKB: (agentId: string, kbId: string) =>
    apiClient.post(`/agents/${agentId}/knowledge-bases/${kbId}`),

  detachKB: (agentId: string, kbId: string) =>
    apiClient.delete(`/agents/${agentId}/knowledge-bases/${kbId}`),

};
