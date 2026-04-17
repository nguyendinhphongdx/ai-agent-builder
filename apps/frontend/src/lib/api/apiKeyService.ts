import { apiClient } from "./client";

export interface ApiKeyResponse {
  id: string;
  provider: string;
  name: string;
  is_default: boolean;
  masked_key: string;
  last_used_at: string | null;
  created_at: string;
}

export interface ApiKeyCreatePayload {
  provider: string;
  name: string;
  plaintext_key: string;
  is_default: boolean;
}

export const apiKeyService = {
  list: (): Promise<ApiKeyResponse[]> =>
    apiClient.get<ApiKeyResponse[]>("/api-keys").then((r) => r.data),

  create: (data: ApiKeyCreatePayload): Promise<ApiKeyResponse> =>
    apiClient.post<ApiKeyResponse>("/api-keys", data).then((r) => r.data),

  update: (id: string, data: Partial<ApiKeyCreatePayload>): Promise<ApiKeyResponse> =>
    apiClient.patch<ApiKeyResponse>(`/api-keys/${id}`, data).then((r) => r.data),

  remove: (id: string): Promise<void> =>
    apiClient.delete(`/api-keys/${id}`).then(() => undefined),
};
