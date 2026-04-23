"use client";

import { memo } from "react";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatRenderMeta, Message } from "../types";
import { StreamMarkdown } from "./StreamMarkdown";
import { MessageAttachments } from "./MessageAttachments";

export type MessageBubbleVariant = "full" | "compact";

interface MessageBubbleProps {
  message: Message;
  variant?: MessageBubbleVariant;
  /** Display info for each role (avatar, name, …). See ChatRenderMeta. */
  meta?: ChatRenderMeta;
}

/**
 * Shared avatar — renders image when URL given, else icon fallback per role.
 * Exported so StreamingBubble can reuse the same styling.
 */
export function ChatAvatar({
  role,
  avatar,
  isCompact,
}: {
  role: "user" | "assistant";
  avatar?: string | null;
  isCompact: boolean;
}) {
  const isUser = role === "user";

  const shell = cn(
    "relative flex shrink-0 items-center justify-center overflow-hidden shadow-sm mt-0.5",
    isCompact ? "h-7 w-7 rounded-lg" : "h-8 w-8 rounded-full",
    isUser
      ? avatar
        ? "ring-1 ring-primary/30"
        : "bg-gradient-to-br from-primary to-primary/80 text-primary-foreground ring-1 ring-primary/30"
      : "border border-primary/20 bg-primary/10 text-primary",
  );

  if (avatar) {
    return (
      <div className={shell}>
        {/* Plain <img> — avatar URLs come from arbitrary storage (local, S3, GCS)
            and don't need next/image's optimizer / remotePatterns config. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={avatar}
          alt=""
          className="h-full w-full object-cover"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
      </div>
    );
  }

  return (
    <div className={shell}>
      {isUser ? (
        <User className={isCompact ? "h-3.5 w-3.5" : "h-4 w-4"} />
      ) : (
        <Bot className={isCompact ? "h-3.5 w-3.5" : "h-4 w-4"} />
      )}
    </div>
  );
}

/**
 * Renders a single chat message.
 *
 * - ``full`` (default): main chat page — large avatars, bubble tail on user side,
 *   subtle background for assistant (no bubble, just markdown).
 * - ``compact``: side-panel preview — smaller avatars; assistant as card.
 */
export const MessageBubble = memo(function MessageBubble({
  message,
  variant = "full",
  meta,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isCompact = variant === "compact";
  const attachments = message.attachments ?? [];
  const avatar = isUser ? meta?.user?.avatar : meta?.agent?.avatar;

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <ChatAvatar
        role={isUser ? "user" : "assistant"}
        avatar={avatar}
        isCompact={isCompact}
      />

      {/* Content column */}
      <div
        className={cn(
          "flex min-w-0 flex-col gap-1.5",
          isUser ? "items-end" : "items-start",
          isCompact ? "max-w-[85%]" : "max-w-[78%]",
        )}
      >
        {/* Attachments — above the text bubble so they're always visible */}
        {attachments.length > 0 && (
          <MessageAttachments
            attachments={attachments}
            align={isUser ? "end" : "start"}
          />
        )}

        {/* Text bubble (user) / markdown block (assistant) */}
        {message.content &&
          (isUser ? (
            <div
              className={cn(
                "text-sm shadow-sm",
                // Speech-bubble radius: tighter corner towards the avatar.
                "rounded-2xl rounded-tr-md bg-gradient-to-br from-primary to-primary/90 px-4 py-2.5 text-primary-foreground ring-1 ring-primary/25",
                isCompact && "px-3 py-2",
              )}
            >
              <p className="whitespace-pre-wrap leading-relaxed">
                {message.content}
              </p>
            </div>
          ) : (
            <div
              className={cn(
                "min-w-0 text-sm",
                isCompact
                  ? "rounded-2xl rounded-tl-md border border-border bg-card px-3 py-2 shadow-sm"
                  : "w-full",
              )}
            >
              <StreamMarkdown content={message.content} />
            </div>
          ))}
      </div>
    </div>
  );
});
