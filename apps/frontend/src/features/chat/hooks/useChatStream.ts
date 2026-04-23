"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createChatSSE } from "@/lib/ws/client";
import { chatService } from "../services/chatService";
import { useChatStore } from "../stores/chatStore";
import type { Message, MessageAttachment } from "../types";

export const chatKeys = {
  all: ["chat"] as const,
  messages: (conversationId: string) =>
    [...chatKeys.all, "messages", conversationId] as const,
  conversations: () => [...chatKeys.all, "conversations"] as const,
};

export interface UseChatStreamOptions {
  /** Conversation to stream with. `null` disables the hook. */
  conversationId: string | null;
  /**
   * - ``true`` (default): messages live in the zustand chat store and are
   *   hydrated from the server via React Query. Use for the main chat page.
   * - ``false``: messages are local state that vanishes on unmount. Use for
   *   ephemeral previews (agent editor, playgrounds).
   */
  persist?: boolean;
}

export interface UseChatStreamResult {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  activeTool: string | null;
  sendMessage: (content: string, attachments?: MessageAttachment[]) => void;
  /** Abort any in-flight SSE and reset stream-only state (keeps messages). */
  abort: () => void;
  /** Wipe messages (used by "New session" in previews). */
  clearMessages: () => void;
}

function makeMessage(
  role: Message["role"],
  content: string,
  conversationId: string,
  attachments?: MessageAttachment[],
): Message {
  return {
    id: crypto.randomUUID(),
    conversation_id: conversationId,
    role,
    content,
    content_type: "text",
    tool_calls: null,
    tool_name: null,
    attachments: attachments && attachments.length > 0 ? attachments : undefined,
    token_usage: null,
    latency_ms: null,
    llm_model: null,
    feedback: null,
    created_at: new Date().toISOString(),
  };
}

/**
 * Unified SSE chat stream hook used by both the main chat window and the
 * ephemeral agent-preview. Persist mode reuses the app's zustand chat store;
 * local mode keeps state inside the hook instance.
 */
export function useChatStream(
  options: UseChatStreamOptions,
): UseChatStreamResult {
  const { conversationId, persist = true } = options;

  // ── persist mode: zustand + query hydration ─────────────────────
  const store = useChatStore();
  const queryClient = useQueryClient();

  const { data: initialMessages } = useQuery({
    queryKey: chatKeys.messages(conversationId ?? ""),
    queryFn: () => chatService.getMessages(conversationId as string),
    enabled: persist && !!conversationId,
  });

  useEffect(() => {
    if (!persist) return;
    if (!conversationId) {
      store.setMessages([]);
      store.resetStream();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, persist]);

  useEffect(() => {
    if (!persist) return;
    if (!initialMessages) return;
    if (useChatStore.getState().isStreaming) return;
    useChatStore.getState().setMessages(initialMessages);
  }, [persist, initialMessages]);

  // ── local mode state ────────────────────────────────────────────
  const [localMessages, setLocalMessages] = useState<Message[]>([]);
  const [localStreaming, setLocalStreaming] = useState(false);
  const [localStreamContent, setLocalStreamContent] = useState("");
  const [localActiveTool, setLocalActiveTool] = useState<string | null>(null);
  const localStreamRef = useRef(""); // tracks stream outside React state for flush

  // Reset local state whenever conversation changes
  useEffect(() => {
    if (persist) return;
    setLocalMessages([]);
    setLocalStreaming(false);
    setLocalStreamContent("");
    setLocalActiveTool(null);
    localStreamRef.current = "";
  }, [persist, conversationId]);

  // ── SSE lifecycle ───────────────────────────────────────────────
  const sseRef = useRef<ReturnType<typeof createChatSSE> | null>(null);

  useEffect(() => {
    return () => sseRef.current?.close();
  }, [conversationId]);

  const abort = useCallback(() => {
    sseRef.current?.close();
    sseRef.current = null;
    if (persist) {
      useChatStore.getState().resetStream();
    } else {
      setLocalStreaming(false);
      setLocalStreamContent("");
      setLocalActiveTool(null);
      localStreamRef.current = "";
    }
  }, [persist]);

  const clearMessages = useCallback(() => {
    abort();
    if (persist) {
      useChatStore.getState().setMessages([]);
    } else {
      setLocalMessages([]);
    }
  }, [abort, persist]);

  const sendMessage = useCallback(
    (content: string, attachments: MessageAttachment[] = []) => {
      if (!conversationId) return;
      const attachmentIds = attachments.map((a) => a.id);

      const currentlyStreaming = persist
        ? useChatStore.getState().isStreaming
        : localStreaming;
      if (currentlyStreaming) return;

      const userMsg = makeMessage("user", content, conversationId, attachments);
      if (persist) {
        useChatStore.getState().addMessage(userMsg);
        useChatStore.getState().setStreaming(true);
      } else {
        setLocalMessages((m) => [...m, userMsg]);
        setLocalStreaming(true);
      }

      const sse = createChatSSE({
        conversationId,
        onToken: (c) => {
          if (persist) {
            useChatStore.getState().appendStreamContent(c);
          } else {
            localStreamRef.current += c;
            setLocalStreamContent((prev) => prev + c);
          }
        },
        onToolStart: (name) => {
          if (persist) useChatStore.getState().setActiveTool(name);
          else setLocalActiveTool(name);
        },
        onToolEnd: () => {
          if (persist) useChatStore.getState().setActiveTool(null);
          else setLocalActiveTool(null);
        },
        onDone: () => {
          if (persist) {
            const state = useChatStore.getState();
            if (state.streamingContent) {
              state.addMessage(
                makeMessage("assistant", state.streamingContent, conversationId),
              );
            }
            state.resetStream();
            queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
          } else {
            const finalContent = localStreamRef.current;
            localStreamRef.current = "";
            setLocalStreamContent("");
            if (finalContent) {
              setLocalMessages((m) => [
                ...m,
                makeMessage("assistant", finalContent, conversationId),
              ]);
            }
            setLocalStreaming(false);
            setLocalActiveTool(null);
          }
        },
        onError: (msg) => {
          console.error("Chat stream error:", msg);
          if (persist) useChatStore.getState().resetStream();
          else {
            setLocalStreaming(false);
            setLocalStreamContent("");
            setLocalActiveTool(null);
            localStreamRef.current = "";
          }
        },
      });

      sseRef.current = sse;
      sse.send(content, attachmentIds);
    },
    [conversationId, persist, localStreaming, queryClient],
  );

  if (persist) {
    return {
      messages: store.messages,
      isStreaming: store.isStreaming,
      streamingContent: store.streamingContent,
      activeTool: store.activeToolName,
      sendMessage,
      abort,
      clearMessages,
    };
  }

  return {
    messages: localMessages,
    isStreaming: localStreaming,
    streamingContent: localStreamContent,
    activeTool: localActiveTool,
    sendMessage,
    abort,
    clearMessages,
  };
}
