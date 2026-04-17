"use client";

import { useCallback, useEffect, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createChatSSE } from "@/lib/ws/client";
import { chatService } from "../services/chatService";
import { useChatStore } from "../stores/chatStore";
import type { Message } from "../types";

export const chatKeys = {
  all: ["chat"] as const,
  messages: (conversationId: string) => [...chatKeys.all, "messages", conversationId] as const,
  conversations: () => [...chatKeys.all, "conversations"] as const,
};

export function useChat(conversationId: string) {
  const abortRef = useRef<ReturnType<typeof createChatSSE> | null>(null);
  const queryClient = useQueryClient();
  const store = useChatStore();

  // Load existing messages
  const { data: initialMessages } = useQuery({
    queryKey: chatKeys.messages(conversationId),
    queryFn: () => chatService.getMessages(conversationId),
    enabled: !!conversationId,
  });

  // Clear store when no conversation (new chat)
  useEffect(() => {
    if (!conversationId) {
      store.setMessages([]);
      store.resetStream();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // Hydrate from server — skip while streaming to preserve optimistic messages
  useEffect(() => {
    if (!initialMessages) return;
    if (useChatStore.getState().isStreaming) return;
    useChatStore.getState().setMessages(initialMessages);
  }, [initialMessages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => abortRef.current?.close();
  }, [conversationId]);

  const sendMessage = useCallback(
    (content: string) => {
      // Read current state directly — avoid stale closure
      const { isStreaming } = useChatStore.getState();
      if (!conversationId || isStreaming) return;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        conversation_id: conversationId,
        role: "user",
        content,
        content_type: "text",
        tool_calls: null,
        tool_name: null,
        token_usage: null,
        latency_ms: null,
        llm_model: null,
        feedback: null,
        created_at: new Date().toISOString(),
      };
      store.addMessage(userMsg);
      store.setStreaming(true);

      const sse = createChatSSE({
        conversationId,
        onToken: (c) => useChatStore.getState().appendStreamContent(c),
        onToolStart: (name) => useChatStore.getState().setActiveTool(name),
        onToolEnd: () => useChatStore.getState().setActiveTool(null),
        onDone: () => {
          const state = useChatStore.getState();
          if (state.streamingContent) {
            const assistantMsg: Message = {
              id: crypto.randomUUID(),
              conversation_id: conversationId,
              role: "assistant",
              content: state.streamingContent,
              content_type: "text",
              tool_calls: null,
              tool_name: null,
              token_usage: null,
              latency_ms: null,
              llm_model: null,
              feedback: null,
              created_at: new Date().toISOString(),
            };
            state.addMessage(assistantMsg);
          }
          state.resetStream();
          // Refresh sidebar conversation list
          queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
        },
        onError: (msg) => {
          console.error("Chat error:", msg);
          useChatStore.getState().resetStream();
        },
      });

      abortRef.current = sse;
      sse.send(content);
    },
    [conversationId, store, queryClient]
  );

  return {
    messages: store.messages,
    isStreaming: store.isStreaming,
    streamingContent: store.streamingContent,
    activeToolName: store.activeToolName,
    sendMessage,
  };
}
