import { apiClient } from "./client";

export interface AgentToolPreview {
  id: string;
  name: string;
  tool_name: string;
  description: string | null;
  model_id: string;
}

export interface McpStatusResponse {
  token_ok: boolean;
  token_last_used_at: string | null;
  required_scopes: string[];
  missing_scopes: string[];
  agents: AgentToolPreview[];
}

export const integrationStatusService = {
  mcp: (tokenId: string): Promise<McpStatusResponse> =>
    apiClient
      .get<McpStatusResponse>(`/integrations/mcp/status`, {
        params: { token_id: tokenId },
      })
      .then((r) => r.data),
};
