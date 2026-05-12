import { apiClient } from "./client";

export interface KBConnector {
  id: string;
  knowledge_base_id: string;
  connector_type: string;
  name: string;
  config: Record<string, unknown>;
  is_active: boolean;
  last_sync_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface KBConnectorCreatePayload {
  connector_type: string;
  name: string;
  config: Record<string, unknown>;
  credentials?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface KBConnectorUpdatePayload {
  name?: string;
  config?: Record<string, unknown>;
  credentials?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface KBConnectorSyncResult {
  discovered: number;
  fetched: number;
  failed: number;
  errors: string[];
}

export const kbConnectorsService = {
  list: (kbId: string): Promise<KBConnector[]> =>
    apiClient
      .get<KBConnector[]>(`/knowledge-bases/${kbId}/connectors`)
      .then((r) => r.data),
  create: (kbId: string, payload: KBConnectorCreatePayload) =>
    apiClient
      .post<KBConnector>(`/knowledge-bases/${kbId}/connectors`, payload)
      .then((r) => r.data),
  update: (kbId: string, id: string, payload: KBConnectorUpdatePayload) =>
    apiClient
      .patch<KBConnector>(`/knowledge-bases/${kbId}/connectors/${id}`, payload)
      .then((r) => r.data),
  remove: (kbId: string, id: string) =>
    apiClient
      .delete(`/knowledge-bases/${kbId}/connectors/${id}`)
      .then(() => undefined),
  syncNow: (kbId: string, id: string) =>
    apiClient
      .post<KBConnectorSyncResult>(
        `/knowledge-bases/${kbId}/connectors/${id}/sync`,
      )
      .then((r) => r.data),
};
