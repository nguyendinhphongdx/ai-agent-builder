import { apiClient } from "./client";

export interface ShareSettings {
  color?: string;
  // Free-form — backend stores anything we send. Future fields go here.
  [key: string]: unknown;
}

export interface ShareConfig {
  enabled: boolean;
  share_token: string | null;
  settings: ShareSettings;
}

export interface ShareUpdate {
  enabled?: boolean;
  rotate?: boolean;
  settings?: ShareSettings;
}

export const agentShareService = {
  get: (agentId: string): Promise<ShareConfig> =>
    apiClient
      .get<ShareConfig>(`/agents/${agentId}/share`)
      .then((r) => r.data),

  update: (agentId: string, body: ShareUpdate): Promise<ShareConfig> =>
    apiClient
      .patch<ShareConfig>(`/agents/${agentId}/share`, body)
      .then((r) => r.data),
};
