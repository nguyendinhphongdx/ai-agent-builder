"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  hint?: string;
  error?: string;
  type?: "text" | "password" | "email" | "url" | "search" | "tel";
  required?: boolean;
  placeholder?: string;
  autoComplete?: string;
  disabled?: boolean;
  className?: string;
};

/**
 * Composed text input with label + optional hint/error.
 * Token-based: uses `--border`, `--background`, `--destructive` — no raw colors.
 *
 * Prefer this over inline `<input className="...">` blocks inside forms.
 * For settings-tab forms, pair with <SettingsField> instead.
 */
export function TextField({
  label,
  value,
  onChange,
  hint,
  error,
  type = "text",
  required,
  placeholder,
  autoComplete,
  disabled,
  className,
}: TextFieldProps) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1 block text-[11px] font-medium text-muted-foreground">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        autoComplete={autoComplete}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        className={cn(
          "w-full rounded-md border bg-background px-2 py-1.5 text-xs transition-colors outline-none",
          "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50",
          "disabled:cursor-not-allowed disabled:opacity-50",
          error
            ? "border-destructive aria-invalid:ring-destructive/20"
            : "border-border",
        )}
      />
      {error ? (
        <p className="mt-1 text-[10px] text-destructive">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-[10px] text-muted-foreground/70">{hint}</p>
      ) : null}
    </label>
  );
}
