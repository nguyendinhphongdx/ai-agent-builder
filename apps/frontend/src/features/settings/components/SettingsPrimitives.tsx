"use client";

import { cn } from "@/lib/utils";

/**
 * Shared layout primitives for the Settings tabs.
 *
 * Every page composes the same shape: a one-line header + description,
 * then one or more <SettingsCard>s. Centralising them here keeps
 * spacing, typography, and rounded corners identical across tabs —
 * easier to redesign once instead of N times.
 */

export function SettingsPageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="flex items-start justify-between gap-4 pb-6">
      <div className="min-w-0 flex-1">
        <h1 className="font-heading text-xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="mt-1 max-w-2xl text-xs text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </header>
  );
}

export function SettingsCard({
  title,
  description,
  action,
  children,
  className,
  bodyClassName,
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section
      className={cn(
        "rounded-xl border border-border bg-card",
        className,
      )}
    >
      {(title || action) && (
        <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-3.5">
          <div className="min-w-0">
            {title && <h2 className="text-sm font-semibold">{title}</h2>}
            {description && (
              <p className="mt-0.5 text-[11px] text-muted-foreground">{description}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      <div className={cn("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

/** Stack of <SettingsCard>s on a page. */
export function SettingsStack({ children }: { children: React.ReactNode }) {
  return <div className="space-y-4">{children}</div>;
}

/** Form row — a labelled input/control with optional hint underneath.
 *  Stays single-column to keep the read path predictable. */
export function SettingsField({
  label,
  hint,
  children,
  htmlFor,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label
        htmlFor={htmlFor}
        className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground"
      >
        {label}
      </label>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground/70">{hint}</p>}
    </div>
  );
}
