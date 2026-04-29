"use client";

import { useState } from "react";
import { Loader2, Send, Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  useTemplateReviews,
  useUpsertReview,
} from "../hooks/useTemplates";
import type { Review } from "../types";

interface ReviewsSectionProps {
  templateId: string;
  /** True when the current user has forked this template — gates the form. */
  canReview: boolean;
}

export function ReviewsSection({ templateId, canReview }: ReviewsSectionProps) {
  const { data: reviews, isLoading } = useTemplateReviews(templateId);

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold">
        Reviews
        {reviews && reviews.length > 0 && (
          <span className="ml-2 text-xs font-normal text-muted-foreground">
            ({reviews.length})
          </span>
        )}
      </h2>

      {canReview && <ReviewForm templateId={templateId} />}

      {isLoading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      ) : !reviews || reviews.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border bg-card px-4 py-6 text-center text-xs text-muted-foreground">
          No reviews yet. {canReview && "Be the first to share your experience."}
        </p>
      ) : (
        <ul className="space-y-3">
          {reviews.map((r) => (
            <ReviewCard key={r.id} review={r} />
          ))}
        </ul>
      )}
    </section>
  );
}

function ReviewForm({ templateId }: { templateId: string }) {
  const upsert = useUpsertReview(templateId);
  const [rating, setRating] = useState(5);
  const [body, setBody] = useState("");
  const [hovered, setHovered] = useState<number | null>(null);

  const submit = () => {
    if (rating < 1) return;
    upsert.mutate(
      { rating, body: body.trim() || undefined },
      {
        onSuccess: () => {
          // Keep the rating, clear the body to indicate "saved"
          setBody("");
        },
      },
    );
  };

  return (
    <div className="space-y-2 rounded-lg border border-border bg-card p-4">
      <p className="text-xs font-medium text-muted-foreground">
        Share your review
      </p>

      {/* Rating stars */}
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((n) => {
          const active = (hovered ?? rating) >= n;
          return (
            <button
              key={n}
              type="button"
              onClick={() => setRating(n)}
              onMouseEnter={() => setHovered(n)}
              onMouseLeave={() => setHovered(null)}
              className="rounded p-0.5 transition-colors hover:bg-accent"
              aria-label={`${n} star${n > 1 ? "s" : ""}`}
            >
              <Star
                className={`h-5 w-5 ${
                  active
                    ? "fill-amber-400 text-amber-400"
                    : "text-muted-foreground"
                }`}
              />
            </button>
          );
        })}
        <span className="ml-2 text-xs text-muted-foreground">{rating}/5</span>
      </div>

      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Optional: what worked well, what could be improved?"
        rows={3}
        maxLength={2000}
        className="text-xs"
      />

      <div className="flex justify-end">
        <Button
          onClick={submit}
          disabled={upsert.isPending}
          size="sm"
          className="gap-1.5"
        >
          {upsert.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Send className="h-3.5 w-3.5" />
          )}
          Submit review
        </Button>
      </div>
    </div>
  );
}

function ReviewCard({ review }: { review: Review }) {
  return (
    <li className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium">
            {review.user_name ?? "Anonymous"}
          </span>
          <Stars rating={review.rating} />
        </div>
        <span className="text-[10px] text-muted-foreground">
          {new Date(review.created_at).toLocaleDateString()}
        </span>
      </div>
      {review.body && (
        <p className="mt-2 whitespace-pre-wrap text-xs text-muted-foreground">
          {review.body}
        </p>
      )}
    </li>
  );
}

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          className={`h-3 w-3 ${
            n <= rating
              ? "fill-amber-400 text-amber-400"
              : "text-muted-foreground/40"
          }`}
        />
      ))}
    </div>
  );
}
