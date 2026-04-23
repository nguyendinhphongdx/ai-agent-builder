"use client";

import { Loader2 } from "lucide-react";
import Lottie from "lottie-react";
import { cn } from "@/lib/utils";
import thinkingAnimation from "../assets/sparker-thinking.json";
import { ChatAvatar } from "./MessageBubble";
import { StreamMarkdown } from "./StreamMarkdown";
import type { ChatRenderMeta } from "../types";

export type StreamingBubbleVariant = "full" | "compact";
export type ThinkingStyle = "lottie" | "dots";

interface StreamingBubbleProps {
  content: string;
  activeTool: string | null;
  variant?: StreamingBubbleVariant;
  /** What to render when the model hasn't produced its first token yet. */
  thinkingStyle?: ThinkingStyle;
  /** Display info (avatar, name, …). Only the ``agent`` slot is used here. */
  meta?: ChatRenderMeta;
}

/** Three animated dots bouncing in sequence. */
function BouncingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/45 [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/45 [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/45 [animation-delay:300ms]" />
    </div>
  );
}

/**
 * The single "assistant is responding" bubble. Shown while the SSE stream is
 * open. Once the stream ``onDone`` fires the bubble is replaced by a normal
 * MessageBubble.
 */
export function StreamingBubble({
  content,
  activeTool,
  variant = "full",
  thinkingStyle = "lottie",
  meta,
}: StreamingBubbleProps) {
  const isCompact = variant === "compact";
  const agentAvatar = meta?.agent?.avatar;

  // No content yet AND no tool — show thinking indicator
  const isThinking = !content && !activeTool;

  // Lottie lives outside any bubble; for dots we wrap the same way as content
  if (isThinking && thinkingStyle === "lottie" && !isCompact) {
    return (
      <div className="flex gap-3">
        <ChatAvatar role="assistant" avatar={agentAvatar} isCompact={false} />
        <Lottie animationData={thinkingAnimation} loop className="h-10 w-10" />
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <ChatAvatar role="assistant" avatar={agentAvatar} isCompact={isCompact} />

      <div
        className={cn(
          "min-w-0 rounded-2xl text-sm",
          isCompact
            ? "max-w-[85%] border border-border bg-card px-3 py-2 text-card-foreground shadow-sm"
            : "max-w-[80%] bg-muted px-4 py-2.5 text-foreground",
        )}
      >
        {activeTool && (
          <div
            className={cn(
              "mb-2 flex items-center gap-1.5",
              isCompact
                ? "text-[11px] text-amber-600 dark:text-amber-400"
                : "text-xs text-muted-foreground",
            )}
          >
            <Loader2 className="h-3 w-3 animate-spin" />
            Using {activeTool}...
          </div>
        )}

        {content ? (
          <StreamMarkdown content={content} mode="streaming" />
        ) : isThinking ? (
          <BouncingDots />
        ) : null}
      </div>
    </div>
  );
}
