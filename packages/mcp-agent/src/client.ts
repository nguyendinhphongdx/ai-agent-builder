/**
 * Thin HTTP client for the lc-agent public REST API.
 * Talks to ``/api/external/*`` endpoints with a personal access token.
 */

export interface AgentSummary {
  id: string;
  name: string;
  description: string | null;
  model_id: string;
  welcome_message: string | null;
  status: string;
  is_published: boolean;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  response: string;
  tokens_used: number | null;
  latency_ms: number | null;
}

export class LcAgentClient {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string,
  ) {
    if (!baseUrl) throw new Error("AGENTFORGE_API_URL is required");
    if (!token) throw new Error("AGENTFORGE_API_TOKEN is required");
  }

  private headers(): Record<string, string> {
    return {
      Authorization: `Bearer ${this.token}`,
      "Content-Type": "application/json",
    };
  }

  private async json<T>(res: Response): Promise<T> {
    if (!res.ok) {
      const text = await res.text();
      throw new Error(
        `lc-agent ${res.status} ${res.statusText}: ${text.slice(0, 300)}`,
      );
    }
    return (await res.json()) as T;
  }

  async listAgents(): Promise<AgentSummary[]> {
    const res = await fetch(`${this.baseUrl}/external/agents`, {
      headers: this.headers(),
    });
    return this.json<AgentSummary[]>(res);
  }

  async chat(
    agentId: string,
    message: string,
    conversationId?: string,
  ): Promise<ChatResponse> {
    const res = await fetch(
      `${this.baseUrl}/external/agents/${agentId}/chat`,
      {
        method: "POST",
        headers: this.headers(),
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
      },
    );
    return this.json<ChatResponse>(res);
  }
}
