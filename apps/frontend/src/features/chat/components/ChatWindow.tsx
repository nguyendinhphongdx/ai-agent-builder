"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ChatInput } from "./ChatInput";
import { ChatMessageList } from "./ChatMessageList";
import { chatKeys, useChatStream } from "../hooks/useChatStream";
import { chatService } from "../services/chatService";
import type { ChatRenderMeta, Conversation, MessageAttachment } from "../types";

const SUGGESTIONS = [
  "Bạn có thể làm gì?",
  "Giúp tôi phân tích dữ liệu",
  "Viết code cho tôi",
];

interface ChatWindowProps {
  agentId: string;
  conversationId: string | null;
  agentName?: string;
  welcomeMessage?: string;
  meta?: ChatRenderMeta;
}

export function ChatWindow({
  agentId,
  conversationId: initialConversationId,
  agentName,
  welcomeMessage,
  meta,
}: ChatWindowProps) {
  const [conversationId, setConversationId] = useState(initialConversationId);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { messages, isStreaming, streamingContent, activeTool, sendMessage } =
    useChatStream({ conversationId: conversationId ?? null, persist: true });

  // While we lazy-create a conversation, stash the intended payload here so
  // the follow-up effect can actually send it once the ID lands.
  const pendingRef = useRef<{ content: string; attachments: MessageAttachment[] } | null>(null);
  const [creating, setCreating] = useState(false);

  // Sync from parent — including reset to null for new chat
  useEffect(() => {
    setConversationId(initialConversationId);
  }, [initialConversationId]);

  // Send pending message after conversation is created, then sync URL + sidebar
  useEffect(() => {
    if (conversationId && pendingRef.current) {
      const { content, attachments } = pendingRef.current;
      pendingRef.current = null;
      sendMessage(content, attachments);

      if (conversationId !== initialConversationId) {
        router.replace(`/ws/agents/${agentId}/chat?conversationId=${conversationId}`, {
          scroll: false,
        });
      }
    }
  }, [conversationId, sendMessage, initialConversationId, agentId, router]);

  const handleSend = useCallback(
    async (content: string, attachments: MessageAttachment[] = []) => {
      if (isStreaming || creating) return;

      if (!conversationId) {
        // Lazy create conversation on first message
        setCreating(true);
        try {
          const title = content.length > 80 ? content.slice(0, 80) + "…" : content;
          const conv = await chatService.createConversation(agentId, title);

          queryClient.setQueryData<Conversation[]>(
            chatKeys.conversations(),
            (old) => [conv, ...(old ?? [])]
          );

          pendingRef.current = { content, attachments };
          setConversationId(conv.id);
        } finally {
          setCreating(false);
        }
        return;
      }

      sendMessage(content, attachments);
    },
    [agentId, conversationId, isStreaming, creating, sendMessage, queryClient]
  );

  const emptyState = !creating ? (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 shadow-sm">
        <Sparkles className="h-6 w-6 text-primary" />
      </div>
      <h3 className="text-lg font-semibold text-foreground">
        {agentName ?? "AI Assistant"}
      </h3>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        {welcomeMessage || "Xin chào! Tôi có thể giúp gì cho bạn hôm nay?"}
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => handleSend(s)}
            className="rounded-full border border-border bg-background px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-foreground"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  ) : (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );

  return (
    <div className="flex h-full min-h-0 flex-col bg-linear-to-b from-sky-50/40 via-background to-purple-50/30 dark:from-sky-950/20 dark:via-background dark:to-purple-950/15">
      <ScrollArea className="scrollbar-thin min-h-0 flex-1 p-4">
        <ChatMessageList
          messages={messages}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          activeTool={activeTool}
          variant="full"
          thinkingStyle="lottie"
          emptyState={emptyState}
          className="mx-auto max-w-3xl space-y-4"
          meta={meta}
        />
      </ScrollArea>

      <ChatInput onSend={handleSend} disabled={isStreaming || creating} />
    </div>
  );
}
