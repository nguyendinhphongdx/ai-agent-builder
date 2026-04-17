"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Bot, Send, User, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { StreamMarkdown } from "@/features/chat/components/StreamMarkdown";
import { createChatSSE } from "@/lib/ws/client";
import { chatService } from "@/features/chat/services/chatService";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface AgentPreviewChatProps {
  agentId?: string;
  agentName?: string;
  welcomeMessage?: string;
  apiKey?: string;
}

export function AgentPreviewChat({
  agentId,
  agentName,
  welcomeMessage,
  apiKey,
}: AgentPreviewChatProps) {
  const isReady = !!agentId && !!apiKey;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamContent, setStreamContent] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const sseRef = useRef<ReturnType<typeof createChatSSE> | null>(null);
    const streamRef = useRef(""); // tracks accumulated stream content outside React state

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamContent]);

  // Create conversation when agentId + apiKey are both available
  useEffect(() => {
    if (!isReady) return;
    let cancelled = false;
    chatService.createConversation(agentId).then((conv) => {
      if (!cancelled) setConversationId(conv.id);
    });
    return () => {
      cancelled = true;
      sseRef.current?.close();
    };
  }, [agentId, isReady]);

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming || !conversationId || !isReady) return;

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: trimmed },
    ]);
    setInput("");
    setIsStreaming(true);

    const sse = createChatSSE({
      conversationId,
      onToken: (content) => {
        streamRef.current += content;
        setStreamContent((prev) => prev + content);
      },
      onToolStart: (name) => setActiveTool(name),
      onToolEnd: () => setActiveTool(null),
      onDone: () => {
        const finalContent = streamRef.current;
        streamRef.current = "";
        setStreamContent("");
        if (finalContent) {
          setMessages((msgs) => [
            ...msgs,
            { id: crypto.randomUUID(), role: "assistant", content: finalContent },
          ]);
        }
        setIsStreaming(false);
        setActiveTool(null);
      },
      onError: (msg) => {
        console.error("Chat error:", msg);
        setIsStreaming(false);
      },
    });

    sseRef.current = sse;
    sse.send(trimmed);
  }, [input, isStreaming, conversationId, isReady]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const hasMessages = messages.length > 0 || isStreaming;

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
      </div>

      {/* Messages area */}
      <div ref={scrollRef} className="scrollbar-thin flex-1 overflow-auto">
        {!hasMessages ? (
          /* Welcome state */
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
                : !apiKey
                ? "Nhập API key trong tab Model để bắt đầu"
                : "Gửi tin nhắn để bắt đầu cuộc trò chuyện"}
            </p>
          </div>
        ) : (
          <div className="space-y-4 p-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn("flex gap-2.5", msg.role === "user" && "justify-end")}
              >
                {msg.role === "assistant" && (
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10">
                    <Bot className="h-3.5 w-3.5 text-primary" />
                  </div>
                )}

                <div
                  className={cn(
                    "min-w-0 max-w-[85%] rounded-2xl border px-3 py-2 shadow-sm",
                    msg.role === "user"
                      ? "border-primary/40 bg-primary text-primary-foreground"
                      : "border-border bg-card text-card-foreground"
                  )}
                >
                  {msg.role === "user" ? (
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
                  ) : (
                    <StreamMarkdown content={msg.content} />
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/70">
                    <User className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                )}
              </div>
            ))}

            {/* Streaming message */}
            {isStreaming && (
              <div className="flex gap-3">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-primary/25 bg-primary/10">
                  <Bot className="h-3.5 w-3.5 text-primary" />
                </div>
                <div className="min-w-0 max-w-[85%] rounded-2xl border border-border bg-card px-3 py-2 pt-2 text-card-foreground shadow-sm">
                  {activeTool && (
                    <div className="mb-2 flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Using {activeTool}...
                    </div>
                  )}
                  {streamContent ? (
                    <StreamMarkdown content={streamContent} />
                  ) : !activeTool ? (
                    <div className="flex items-center gap-1 py-1">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/45 [animation-delay:0ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/45 [animation-delay:150ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/45 [animation-delay:300ms]" />
                    </div>
                  ) : null}
                </div>
              </div>
            )}
          </div>
        )}
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
                : !apiKey
                ? "Nhập API key trong tab Model…"
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
