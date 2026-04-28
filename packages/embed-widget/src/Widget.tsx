import { useEffect, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";
import { ShareApi, type AgentInfo } from "./api";
import { storage } from "./storage";

interface Msg {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  streaming?: boolean;
}

interface Props {
  apiUrl: string;
  shareToken: string;
}

let nextId = 0;
const newId = () => `m${++nextId}`;

export function Widget({ apiUrl, shareToken }: Props): JSX.Element | null {
  const [open, setOpen] = useState(false);
  const [agent, setAgent] = useState<AgentInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const conversationIdRef = useRef<string | null>(
    storage.loadConversationId(shareToken),
  );
  const apiRef = useRef<ShareApi | null>(null);
  const msgsEndRef = useRef<HTMLDivElement>(null);

  // Load agent metadata once on first open. Defer until panel is opened so
  // the FAB doesn't fire a network request on every page load.
  useEffect(() => {
    if (!open || agent || error) return;
    apiRef.current ??= new ShareApi(apiUrl, shareToken);
    apiRef.current
      .getAgent()
      .then((a) => {
        setAgent(a);
        if (a.welcome_message) {
          setMsgs([
            { id: newId(), role: "assistant", content: a.welcome_message },
          ]);
        }
      })
      .catch((e: Error) => setError(e.message));
  }, [open, agent, error, apiUrl, shareToken]);

  // Auto-scroll on every render where msgs changed.
  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;

    const userMsg: Msg = { id: newId(), role: "user", content: text };
    const aiMsg: Msg = {
      id: newId(),
      role: "assistant",
      content: "",
      streaming: true,
    };
    setMsgs((prev) => [...prev, userMsg, aiMsg]);
    setInput("");
    setBusy(true);

    try {
      const api = apiRef.current!;
      const convId = await api.chatStream(
        text,
        conversationIdRef.current,
        (evt) => {
          if (evt.type === "token" && typeof evt.content === "string") {
            const tok = evt.content;
            setMsgs((prev) =>
              prev.map((m) =>
                m.id === aiMsg.id ? { ...m, content: m.content + tok } : m,
              ),
            );
          } else if (evt.type === "error") {
            setMsgs((prev) =>
              prev.map((m) =>
                m.id === aiMsg.id
                  ? {
                      ...m,
                      role: "error",
                      streaming: false,
                      content: evt.message ?? "Stream error",
                    }
                  : m,
              ),
            );
          }
        },
      );
      if (convId) {
        conversationIdRef.current = convId;
        storage.saveConversationId(shareToken, convId);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setMsgs((prev) =>
        prev.map((m) =>
          m.id === aiMsg.id
            ? { ...m, role: "error", streaming: false, content: msg }
            : m,
        ),
      );
    } finally {
      setMsgs((prev) =>
        prev.map((m) =>
          m.id === aiMsg.id ? { ...m, streaming: false } : m,
        ),
      );
      setBusy(false);
    }
  };

  const onKeyDown: JSX.KeyboardEventHandler<HTMLTextAreaElement> = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  if (!open) {
    return (
      <button
        class="fab"
        onClick={() => setOpen(true)}
        aria-label="Open chat"
      >
        <svg viewBox="0 0 24 24">
          <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z" />
        </svg>
      </button>
    );
  }

  const initial = (agent?.name || "A").slice(0, 1).toUpperCase();

  return (
    <div class="panel" role="dialog" aria-label="Chat panel">
      <div class="head">
        <div class="avatar">
          {agent?.avatar_url ? <img src={agent.avatar_url} alt="" /> : initial}
        </div>
        <div class="meta">
          <div class="name">{agent?.name ?? "Loading…"}</div>
          {agent?.description && (
            <div class="desc">{agent.description}</div>
          )}
        </div>
        <button
          class="close"
          onClick={() => setOpen(false)}
          aria-label="Close"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
          </svg>
        </button>
      </div>

      <div class="msgs">
        {error && <div class="msg err">{error}</div>}
        {msgs.map((m) => (
          <div
            key={m.id}
            class={`msg ${m.role === "user" ? "u" : m.role === "error" ? "err" : "a"}`}
          >
            {m.content}
            {m.streaming && <span class="cursor" />}
          </div>
        ))}
        <div ref={msgsEndRef} />
      </div>

      <div class="foot">
        <textarea
          rows={1}
          placeholder="Ask anything…"
          value={input}
          onInput={(e) =>
            setInput((e.currentTarget as HTMLTextAreaElement).value)
          }
          onKeyDown={onKeyDown}
          disabled={busy || !!error || !agent}
        />
        <button
          onClick={send}
          disabled={busy || !input.trim() || !!error || !agent}
          aria-label="Send"
        >
          <svg viewBox="0 0 24 24">
            <path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>

      <div class="brand">
        Powered by <a href="https://agentforge.ai" target="_blank" rel="noopener">AgentForge</a>
      </div>
    </div>
  );
}
