"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, Loader2, Sparkles } from "lucide-react";
import Lottie from "lottie-react";
import thinkingAnimation from "../assets/sparker-thinking.json";
import { useQueryClient } from "@tanstack/react-query";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { StreamMarkdown } from "./StreamMarkdown";
import { useChat, chatKeys } from "../hooks/useChat";
import { chatService } from "../services/chatService";
import type { Conversation } from "../types";

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
}

export function ChatWindow({
  agentId,
  conversationId: initialConversationId,
  agentName,
  welcomeMessage,
}: ChatWindowProps) {
  const [conversationId, setConversationId] = useState(initialConversationId);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { messages, isStreaming, streamingContent, activeToolName, sendMessage } =
    useChat(conversationId ?? "");
  const bottomRef = useRef<HTMLDivElement>(null);
  const pendingRef = useRef<string | null>(null);
  const [creating, setCreating] = useState(false);

  // Sync from parent — including reset to null for new chat
  useEffect(() => {
    setConversationId(initialConversationId);
  }, [initialConversationId]);

  // Send pending message after conversation is created, then sync URL + sidebar
  useEffect(() => {
    if (conversationId && pendingRef.current) {
      const msg = pendingRef.current;
      pendingRef.current = null;
      sendMessage(msg);

      if (conversationId !== initialConversationId) {
        // Sync URL so sidebar can highlight active conversation
        router.replace(`/agents/${agentId}/chat?conversationId=${conversationId}`, {
          scroll: false,
        });
      }
    }
  }, [conversationId, sendMessage, initialConversationId, agentId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = useCallback(
    async (content: string) => {
      if (isStreaming || creating) return;

      if (!conversationId) {
        // Lazy create conversation on first message
        setCreating(true);
        try {
          const title = content.length > 80 ? content.slice(0, 80) + "…" : content;
          const conv = await chatService.createConversation(agentId, title);

          // Add to sidebar list immediately (optimistic)
          queryClient.setQueryData<Conversation[]>(
            chatKeys.conversations(),
            (old) => [conv, ...(old ?? [])]
          );

          pendingRef.current = content;
          setConversationId(conv.id);
        } finally {
          setCreating(false);
        }
        return;
      }

      sendMessage(content);
    },
    [agentId, conversationId, isStreaming, creating, sendMessage, queryClient]
  );

  const hasContent = messages.length > 0 || isStreaming;

  return (
    <div className="flex h-full min-h-0 flex-col bg-linear-to-b from-sky-50/40 via-background to-purple-50/30 dark:from-sky-950/20 dark:via-background dark:to-purple-950/15">
      <ScrollArea className="scrollbar-thin min-h-0 flex-1 p-4">
        <div className="mx-auto max-w-3xl space-y-4">
          {/* Welcome state */}
          {!hasContent && !creating && (
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
          )}

          {/* Creating conversation spinner */}
          {creating && (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          {isStreaming && (
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                <Bot className="h-4 w-4" />
              </div>
              {streamingContent || activeToolName ? (
                <div className="min-w-0 max-w-[80%] rounded-2xl bg-muted px-4 py-2.5 text-sm">
                  {activeToolName && (
                    <div className="mb-2 flex items-center gap-2 text-xs text-muted-foreground">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Using {activeToolName}...
                    </div>
                  )}
                  {streamingContent && (
                    <StreamMarkdown content={streamingContent} mode="streaming" />
                  )}
                </div>
              ) : (
                <Lottie
                  animationData={thinkingAnimation}
                  loop
                  className="h-10 w-10"
                />
              )}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <ChatInput onSend={handleSend} disabled={isStreaming || creating} />
    </div>
  );
}
