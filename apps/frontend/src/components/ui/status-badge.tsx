"use client";

import { Badge } from "./badge";

/**
 * Semantic status pill. Use this anywhere you'd otherwise write
 * `bg-emerald-500/15 text-emerald-700 dark:text-emerald-300` —
 * the tone token + dark-mode handling lives here once.
 *
 * Tones map to design tokens:
 *   - `active`        → success (was emerald-*)
 *   - `inactive`      → muted (neutral grey)
 *   - `pending`       → warning (was amber-*)
 *   - `failed`        → destructive (was red/rose-*)
 *   - `info`          → info (was blue-*)
 *
 * For raw badge styling (non-status), use `<Badge variant="...">` directly.
 */
export type StatusTone =
  | "active"
  | "inactive"
  | "pending"
  | "failed"
  | "info";

const TONE_VARIANT: Record<
  StatusTone,
  "success" | "outline" | "warning" | "destructive" | "info"
> = {
  active: "success",
  inactive: "outline",
  pending: "warning",
  failed: "destructive",
  info: "info",
};

export function StatusBadge({
  tone,
  children,
  className,
}: {
  tone: StatusTone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Badge variant={TONE_VARIANT[tone]} className={className}>
      {children}
    </Badge>
  );
}
