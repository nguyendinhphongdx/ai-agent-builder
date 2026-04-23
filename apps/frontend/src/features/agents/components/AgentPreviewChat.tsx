"use client";

import { useCallback, useEffect, useState } from "react";
import { Bot, RotateCcw, Send, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ChatMessageList } from "@/features/chat/components/ChatMessageList";
import { useChatStream } from "@/features/chat/hooks/useChatStream";
import { chatService } from "@/features/chat/services/chatService";

interface AgentPreviewChatProps {
  agentId?: string;
  agentName?: string;
  agentAvatar?: string | null;
  welcomeMessage?: string;
  credentialReady?: boolean;
}

export function AgentPreviewChat({
  agentId,
  agentName,
  agentAvatar,
  welcomeMessage,
  credentialReady,
}: AgentPreviewChatProps) {
  const isReady = !!agentId && !!credentialReady;
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");

  const { messages, isStreaming, streamingContent, activeTool, sendMessage, abort, clearMessages } =
    useChatStream({ conversationId, persist: false });

  // Create conversation eagerly when agent + credential are ready
  useEffect(() => {
    if (!isReady || !agentId) return;
    let cancelled = false;
    chatService.createConversation(agentId).then((conv) => {
      if (!cancelled) setConversationId(conv.id);
    });
    return () => {
      cancelled = true;
    };
  }, [agentId, isReady]);

  const hasMessages = messages.length > 0 || isStreaming;

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || !conversationId || !isReady) return;
    sendMessage(trimmed);
    setInput("");
  }, [input, isStreaming, conversationId, isReady, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewSession = useCallback(() => {
    if (!isReady || !agentId) return;
    abort();
    clearMessages();
    setInput("");
    setConversationId(null);
    chatService.createConversation(agentId).then((conv) => {
      setConversationId(conv.id);
    });
  }, [isReady, agentId, abort, clearMessages]);

  const emptyState = (
    <div className="flex h-full flex-col items-center justify-center px-6 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/25 bg-primary/10 shadow-sm">
        <Sparkles className="h-5 w-5 text-primary" />
      </div>
      <p className="text-sm font-medium text-foreground/90">
        {welcomeMessage || "Test your agent here"}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">
        {!agentId
          ? "Lưu agent trước để bật chat preview"
          : !credentialReady
            ? "Kết nối credential trong tab Model để bắt đầu"
            : "Gửi tin nhắn để bắt đầu cuộc trò chuyện"}
      </p>
    </div>
  );

  return (
    <div className="flex h-full flex-col border-l border-border bg-gradient-to-b from-background via-background to-muted/35">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border/70 bg-background/80 px-4 py-2.5 backdrop-blur">
        <div className="flex h-6 w-6 items-center justify-center rounded-md border border-primary/30 bg-primary/10">
          <Bot className="h-3 w-3 text-primary" />
        </div>
        <span className="text-xs font-medium text-foreground/80">Preview</span>
        {agentName && (
          <>
            <span className="text-foreground/20">·</span>
            <span className="text-xs text-muted-foreground">{agentName}</span>
          </>
        )}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleNewSession}
          disabled={!isReady || (!hasMessages && !conversationId)}
          className="ml-auto h-7 gap-1.5 px-2 text-[11px] text-muted-foreground hover:text-foreground"
          title="Bắt đầu cuộc hội thoại mới"
        >
          <RotateCcw className="h-3 w-3" />
          New session
        </Button>
      </div>

      {/* Messages area */}
      <div className="scrollbar-thin flex-1 overflow-auto">
        <ChatMessageList
          messages={messages}
          isStreaming={isStreaming}
          streamingContent={streamingContent}
          activeTool={activeTool}
          variant="compact"
          thinkingStyle="dots"
          emptyState={emptyState}
          className="space-y-4 p-4"
          meta={{ agent: { name: agentName, avatar: agentAvatar } }}
        />
      </div>

      {/* Input */}
      <div className="border-t border-border/70 bg-background/80 p-3 backdrop-blur">
        <div className="flex items-end gap-2">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              !agentId
                ? "Lưu agent để bật preview…"
                : !credentialReady
                  ? "Kết nối credential trong tab Model…"
                  : "Gửi tin nhắn…"
            }
            disabled={!isReady || isStreaming}
            className="min-h-[38px] max-h-[110px] resize-none border-border bg-muted/60 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/40 focus-visible:ring-1 focus-visible:ring-primary/30"
            rows={1}
          />
          <Button
            onClick={handleSend}
            disabled={!isReady || isStreaming || !input.trim()}
            size="icon"
            className="h-9 w-9 shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground"
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
