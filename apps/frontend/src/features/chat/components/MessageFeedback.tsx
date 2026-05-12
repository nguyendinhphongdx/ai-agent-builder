"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ThumbsDown, ThumbsUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { annotationsService } from "@/lib/api/annotationsService";

/**
 * Thumbs up / down for one assistant message.
 *
 * Click flow:
 *   - Click 👍 / 👎 → upsert with no feedback (fast path).
 *   - On 👎, surface a tiny text area for optional "why?". Blank
 *     submit is fine; the rating is saved either way.
 *   - Click an already-active vote → DELETE (toggle off).
 *
 * No optimistic UI — the network call is fast and the visual
 * change after the refetch reads as clear feedback.
 */
export function MessageFeedback({ messageId }: { messageId: string }) {
  const qc = useQueryClient();
  const annoQ = useQuery({
    queryKey: ["annotation", messageId],
    queryFn: () => annotationsService.get(messageId),
    staleTime: 60_000,
  });

  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState("");

  const upsert = useMutation({
    mutationFn: (rating: -1 | 1) =>
      annotationsService.upsert(messageId, {
        rating,
        feedback: rating === -1 && feedback.trim() ? feedback.trim() : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["annotation", messageId] });
    },
  });

  const remove = useMutation({
    mutationFn: () => annotationsService.remove(messageId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["annotation", messageId] });
      setShowFeedback(false);
      setFeedback("");
    },
  });

  const current = annoQ.data?.rating;

  const handleVote = (rating: -1 | 1) => {
    if (current === rating) {
      remove.mutate();
      return;
    }
    if (rating === -1) {
      setShowFeedback(true);
    } else {
      setShowFeedback(false);
    }
    upsert.mutate(rating);
  };

  return (
    <div className="mt-1 flex flex-col gap-1.5">
      <div className="flex items-center gap-0.5 opacity-60 transition-opacity hover:opacity-100">
        <button
          type="button"
          onClick={() => handleVote(1)}
          aria-label="Thumbs up"
          title="Helpful"
          className={cn(
            "rounded-md p-1 transition-colors hover:bg-accent",
            current === 1 && "bg-emerald-500/15 text-emerald-600",
          )}
        >
          <ThumbsUp className="h-3 w-3" />
        </button>
        <button
          type="button"
          onClick={() => handleVote(-1)}
          aria-label="Thumbs down"
          title="Not helpful"
          className={cn(
            "rounded-md p-1 transition-colors hover:bg-accent",
            current === -1 && "bg-rose-500/15 text-rose-600",
          )}
        >
          <ThumbsDown className="h-3 w-3" />
        </button>
      </div>
      {showFeedback && current === -1 && (
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="What went wrong? (optional)"
            className="w-64 rounded-md border border-border bg-background px-2 py-1 text-[11px]"
          />
          <button
            type="button"
            onClick={() => {
              upsert.mutate(-1);
              setShowFeedback(false);
            }}
            className="rounded-md bg-primary px-2 py-1 text-[11px] text-primary-foreground hover:bg-primary/90"
          >
            Save
          </button>
        </div>
      )}
    </div>
  );
}
