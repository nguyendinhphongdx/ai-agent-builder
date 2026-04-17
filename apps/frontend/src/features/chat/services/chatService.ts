import { apiClient } from "@/lib/api/client";
import type { Conversation, Message } from "../types";

export const chatService = {
  listConversations: (agentId?: string) => {
    const params = agentId ? { agent_id: agentId } : {};
    return apiClient.get<Conversation[]>("/conversations", { params }).then((r) => r.data);
  },

  createConversation: (agentId: string, title?: string) =>
    apiClient
      .post<Conversation>("/conversations", { agent_id: agentId, title })
      .then((r) => r.data),

  getMessages: (conversationId: string) =>
    apiClient
      .get<Message[]>(`/conversations/${conversationId}/messages`)
      .then((r) => r.data),
};
