import { apiClient } from "@/lib/api/client";
import type { KnowledgeBase, KBDocument } from "../types";

export const knowledgeService = {
  list: () =>
    apiClient.get<KnowledgeBase[]>("/knowledge-bases").then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<KnowledgeBase>(`/knowledge-bases/${id}`).then((r) => r.data),

  getByAgentId: (agentId: string) =>
    apiClient
      .get<{ knowledge_bases: KnowledgeBase[] }>(`/agents/${agentId}`)
      .then((r) => r.data.knowledge_bases ?? []),

  create: (data: { name: string; description?: string }) =>
    apiClient.post<KnowledgeBase>("/knowledge-bases", data).then((r) => r.data),

  delete: (id: string) =>
    apiClient.delete(`/knowledge-bases/${id}`),

  listDocuments: (kbId: string) =>
    apiClient.get<KBDocument[]>(`/knowledge-bases/${kbId}/documents`).then((r) => r.data),

  uploadDocument: (kbId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiClient
      .post<KBDocument>(`/knowledge-bases/${kbId}/documents`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  deleteDocument: (kbId: string, docId: string) =>
    apiClient.delete(`/knowledge-bases/${kbId}/documents/${docId}`),

  attachToAgent: (agentId: string, kbId: string) =>
    apiClient.post(`/agents/${agentId}/knowledge-bases/${kbId}`),
};
