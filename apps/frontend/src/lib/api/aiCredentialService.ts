import { apiClient } from "./client";

export interface AICredentialResponse {
  id: string;
  provider: string;
  name: string;
  masked_key: string;
  last_used_at: string | null;
  created_at: string;
}

export interface AICredentialCreatePayload {
  provider: string;
  name: string;
  plaintext_key: string;
}

export interface AICredentialUpdatePayload {
  name?: string;
}

export const aiCredentialService = {
  list: (): Promise<AICredentialResponse[]> =>
    apiClient.get<AICredentialResponse[]>("/ai-credentials").then((r) => r.data),

  create: (data: AICredentialCreatePayload): Promise<AICredentialResponse> =>
    apiClient.post<AICredentialResponse>("/ai-credentials", data).then((r) => r.data),

  update: (
    id: string,
    data: AICredentialUpdatePayload,
  ): Promise<AICredentialResponse> =>
    apiClient
      .patch<AICredentialResponse>(`/ai-credentials/${id}`, data)
      .then((r) => r.data),

  remove: (id: string): Promise<void> =>
    apiClient.delete(`/ai-credentials/${id}`).then(() => undefined),
};
