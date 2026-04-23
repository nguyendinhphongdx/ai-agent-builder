import { apiClient } from "@/lib/api/client";
import type {
  KnowledgeBase,
  KBChunkListResponse,
  KBCreateInput,
  KBDocument,
  KBDocumentDetail,
  KBUpdateInput,
  RetrievedChunk,
} from "../types";

export const knowledgeService = {
  list: () =>
    apiClient.get<KnowledgeBase[]>("/knowledge-bases").then((r) => r.data),

  getById: (id: string) =>
    apiClient.get<KnowledgeBase>(`/knowledge-bases/${id}`).then((r) => r.data),

  getByAgentId: (agentId: string) =>
    apiClient
      .get<{ knowledge_bases: KnowledgeBase[] }>(`/agents/${agentId}`)
      .then((r) => r.data.knowledge_bases ?? []),

  create: (data: KBCreateInput) =>
    apiClient.post<KnowledgeBase>("/knowledge-bases", data).then((r) => r.data),

  update: (id: string, data: KBUpdateInput) =>
    apiClient.put<KnowledgeBase>(`/knowledge-bases/${id}`, data).then((r) => r.data),

  delete: (id: string) => apiClient.delete(`/knowledge-bases/${id}`),

  listDocuments: (kbId: string) =>
    apiClient.get<KBDocument[]>(`/knowledge-bases/${kbId}/documents`).then((r) => r.data),

  getDocument: (kbId: string, docId: string) =>
    apiClient
      .get<KBDocumentDetail>(`/knowledge-bases/${kbId}/documents/${docId}`)
      .then((r) => r.data),

  listChunks: (kbId: string, docId: string, limit = 50, offset = 0) =>
    apiClient
      .get<KBChunkListResponse>(
        `/knowledge-bases/${kbId}/documents/${docId}/chunks`,
        { params: { limit, offset } },
      )
      .then((r) => r.data),

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

  query: (kbId: string, query: string, topK = 5) =>
    apiClient
      .post<RetrievedChunk[]>(`/knowledge-bases/${kbId}/query`, { query, top_k: topK })
      .then((r) => r.data),

  attachToAgent: (agentId: string, kbId: string) =>
    apiClient.post(`/agents/${agentId}/knowledge-bases/${kbId}`),

  detachFromAgent: (agentId: string, kbId: string) =>
    apiClient.delete(`/agents/${agentId}/knowledge-bases/${kbId}`),
};
