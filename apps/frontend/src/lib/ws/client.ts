export type SSEMessage =
  | { type: "token"; content: string }
  | { type: "tool_start"; name: string }
  | { type: "tool_end"; name: string; result: string }
  | { type: "done" }
  | { type: "error"; message: string };

interface ChatSSEOptions {
  conversationId: string;
  onToken: (content: string) => void;
  onToolStart: (name: string) => void;
  onToolEnd: (name: string, result: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
}

export function createChatSSE(options: ChatSSEOptions) {
  let abortController: AbortController | null = null;

  const send = async (content: string, attachmentIds: string[] = []) => {
    abortController = new AbortController();
    const baseUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

    try {
      const response = await fetch(
        `${baseUrl}/conversations/${options.conversationId}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ content, attachment_ids: attachmentIds }),
          signal: abortController.signal,
        }
      );

      if (!response.ok || !response.body) {
        options.onError(`HTTP ${response.status}`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop() ?? "";

        for (const chunk of chunks) {
          const line = chunk.trim();
          if (!line.startsWith("data: ")) continue;
          try {
            const msg: SSEMessage = JSON.parse(line.slice(6));
            switch (msg.type) {
              case "token":
                options.onToken(msg.content);
                break;
              case "tool_start":
                options.onToolStart(msg.name);
                break;
              case "tool_end":
                options.onToolEnd(msg.name, msg.result);
                break;
              case "done":
                options.onDone();
                break;
              case "error":
                options.onError(msg.message);
                break;
            }
          } catch {
            // malformed event — skip
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        options.onError("Connection error");
      }
    }
  };

  return {
    send,
    close: () => abortController?.abort(),
  };
}

// Legacy alias — remove after all callers are updated
export const createChatWS = createChatSSE;

