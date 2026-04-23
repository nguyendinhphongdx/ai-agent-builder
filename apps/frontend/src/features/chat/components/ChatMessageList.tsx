"use client";

import { useEffect, useRef, type ReactNode } from "react";
import type { ChatRenderMeta, Message } from "../types";
import { MessageBubble } from "./MessageBubble";
import { StreamingBubble, type ThinkingStyle } from "./StreamingBubble";

export type ChatListVariant = "full" | "compact";

interface ChatMessageListProps {
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  activeTool: string | null;
  variant?: ChatListVariant;
  thinkingStyle?: ThinkingStyle;
  /** Shown when there are no messages and no active stream. */
  emptyState?: ReactNode;
  className?: string;
  /** Extra content after the bubbles, before the scroll anchor. */
  footer?: ReactNode;
  /** Display info for user + agent (avatars, names, …). */
  meta?: ChatRenderMeta;
}

/**
 * Reusable message-list rendering shared by ChatWindow and AgentPreviewChat.
 * Handles auto-scroll-to-bottom whenever messages or the streaming buffer
 * change. Owners supply their own welcome/empty content via ``emptyState``.
 */
export function ChatMessageList({
  messages,
  isStreaming,
  streamingContent,
  activeTool,
  variant = "full",
  thinkingStyle = "lottie",
  emptyState,
  className,
  footer,
  meta,
}: ChatMessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className={className}>
      {isEmpty && emptyState}

      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} variant={variant} meta={meta} />
      ))}

      {isStreaming && (
        <StreamingBubble
          content={streamingContent}
          activeTool={activeTool}
          variant={variant}
          thinkingStyle={thinkingStyle}
          meta={meta}
        />
      )}

      {footer}

      <div ref={bottomRef} />
    </div>
  );
}
