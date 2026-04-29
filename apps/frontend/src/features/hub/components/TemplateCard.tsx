"use client";

import Link from "next/link";
import { Star, Bot, Users, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { TemplateSummary } from "../types";

interface TemplateCardProps {
  template: TemplateSummary;
}

export function TemplateCard({ template }: TemplateCardProps) {
  const isFree = template.price_cents === 0;
  const priceLabel = isFree
    ? "Free"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: template.currency || "USD",
      }).format(template.price_cents / 100);

  return (
    <Link
      href={`/hub/${template.slug}`}
      className="group flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-all hover:shadow-sm hover:border-violet-200 dark:hover:border-violet-500/30"
    >
      {/* Cover */}
      <div className="relative aspect-[16/10] overflow-hidden rounded-lg bg-gradient-to-br from-violet-100 to-violet-200 dark:from-violet-500/20 dark:to-violet-700/20">
        {template.cover_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={template.cover_image_url}
            alt={template.title}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <Bot className="h-10 w-10 text-violet-500/60" />
          </div>
        )}
        {template.is_featured && (
          <Badge className="absolute left-2 top-2 gap-1 bg-amber-500 text-white border-0">
            <Sparkles className="h-3 w-3" />
            Featured
          </Badge>
        )}
      </div>

      {/* Title + author */}
      <div className="space-y-1">
        <h3 className="line-clamp-1 text-sm font-semibold group-hover:text-violet-600 dark:group-hover:text-violet-400">
          {template.title}
        </h3>
        <p className="text-[11px] text-muted-foreground">by {template.author_name}</p>
      </div>

      {/* Description */}
      {template.description && (
        <p className="line-clamp-2 text-xs text-muted-foreground">
          {template.description}
        </p>
      )}

      {/* Footer: price + stats */}
      <div className="mt-auto flex items-center justify-between pt-2">
        <span
          className={`text-xs font-semibold ${
            isFree ? "text-emerald-600 dark:text-emerald-400" : "text-foreground"
          }`}
        >
          {priceLabel}
        </span>
        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            {template.fork_count}
          </span>
          {template.rating_count > 0 && (
            <span className="flex items-center gap-1">
              <Star className="h-3 w-3" />
              {Number(template.rating_avg ?? 0).toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
