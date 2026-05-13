"use client";

import { cn } from "@/lib/utils";

type TextareaFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  hint?: string;
  error?: string;
  required?: boolean;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
};

export function TextareaField({
  label,
  value,
  onChange,
  rows = 3,
  hint,
  error,
  required,
  placeholder,
  disabled,
  className,
}: TextareaFieldProps) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1 block text-[11px] font-medium text-muted-foreground">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </span>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        required={required}
        placeholder={placeholder}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        className={cn(
          "w-full rounded-md border bg-background px-2 py-1.5 text-xs transition-colors outline-none resize-y",
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
