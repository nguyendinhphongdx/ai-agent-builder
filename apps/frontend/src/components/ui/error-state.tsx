"use client";

import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

/**
 * Shared error display — replaces ad-hoc `border-red-500/40 bg-red-500/10`
 * banners scattered across features. Two variants:
 *
 *   - `inline` (default): compact banner suitable for forms / list rows
 *   - `block`: full panel with icon + retry button for empty/page states
 *
 * Always uses the `--destructive` token (light + dark via globals.css).
 */
type ErrorStateProps = {
  message: string;
  title?: string;
  variant?: "inline" | "block";
  onRetry?: () => void;
  className?: string;
};

export function ErrorState({
  message,
  title,
  variant = "inline",
  onRetry,
  className,
}: ErrorStateProps) {
  if (variant === "inline") {
    return (
      <div
        role="alert"
        className={cn(
          "flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive",
          className,
        )}
      >
        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <div className="min-w-0 flex-1">
          {title && <div className="font-medium">{title}</div>}
          <div className={cn(title && "mt-0.5 opacity-90")}>{message}</div>
        </div>
        {onRetry && (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={onRetry}
            className="h-6 px-2 text-xs text-destructive hover:bg-destructive/15 hover:text-destructive"
          >
            Retry
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/5 px-6 py-8 text-center",
        className,
      )}
    >
      <AlertCircle className="h-8 w-8 text-destructive" />
      {title && (
        <h3 className="text-sm font-semibold text-destructive">{title}</h3>
      )}
      <p className="max-w-md text-xs text-muted-foreground">{message}</p>
      {onRetry && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onRetry}
          className="mt-2"
        >
          Try again
        </Button>
      )}
    </div>
  );
}
