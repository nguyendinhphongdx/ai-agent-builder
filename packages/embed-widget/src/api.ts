/**
 * Thin wrapper around the AgentForge share endpoints.
 * No third-party deps — uses native fetch + ReadableStream for SSE.
 */

export interface AgentInfo {
  id: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  welcome_message: string | null;
  settings: Record<string, unknown>;
}

export interface StreamEvent {
  type: "meta" | "token" | "tool_start" | "tool_end" | "done" | "error";
  content?: string;
  conversation_id?: string;
  message?: string;
  // tool events carry tool-specific fields we don't render in the widget;
  // forwarded as `unknown` so callers can ignore them safely.
  [key: string]: unknown;
}

export class ShareApi {
  constructor(
    private readonly apiUrl: string,
    private readonly shareToken: string,
  ) {}

  async getAgent(): Promise<AgentInfo> {
    const r = await fetch(
      `${this.apiUrl}/share/${this.shareToken}/agent`,
      { headers: { Accept: "application/json" } },
    );
    if (!r.ok) {
      const txt = await r.text().catch(() => "");
      throw new Error(`Agent fetch failed: ${r.status} ${txt}`);
    }
    return r.json();
  }

  /**
   * Stream a chat turn. Calls onEvent for each parsed SSE frame; resolves
   * after the `done` frame or rejects on transport errors.
   *
   * Returns the conversation_id reported by the first `meta` event so
   * callers can persist it for follow-up turns.
   */
  async chatStream(
    message: string,
    conversationId: string | null,
    onEvent: (e: StreamEvent) => void,
    signal?: AbortSignal,
  ): Promise<string | null> {
    const r = await fetch(
      `${this.apiUrl}/share/${this.shareToken}/stream`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
        signal,
      },
    );
    if (!r.ok || !r.body) {
      const txt = await r.text().catch(() => "");
      throw new Error(`Stream failed: ${r.status} ${txt}`);
    }

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let convId: string | null = conversationId;

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      // SSE frames are separated by a blank line. Process complete frames
      // only — keep the trailing partial in the buffer for the next chunk.
      let sep;
      while ((sep = buf.indexOf("\n\n")) !== -1) {
        const frame = buf.slice(0, sep);
        buf = buf.slice(sep + 2);
        const dataLine = frame
          .split("\n")
          .find((l) => l.startsWith("data:"));
        if (!dataLine) continue;
        try {
          const evt: StreamEvent = JSON.parse(dataLine.slice(5).trim());
          if (evt.type === "meta" && evt.conversation_id) {
            convId = evt.conversation_id;
          }
          onEvent(evt);
          if (evt.type === "done") return convId;
        } catch {
          // Ignore malformed frames; keeping the connection alive is more
          // valuable than crashing on a single bad event.
        }
      }
    }
    return convId;
  }
}
