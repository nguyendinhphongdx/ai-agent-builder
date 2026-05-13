"use client";

import { cn } from "@/lib/utils";

type NumberFieldProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  hint?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
};

export function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step,
  hint,
  error,
  required,
  disabled,
  className,
}: NumberFieldProps) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1 block text-[11px] font-medium text-muted-foreground">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(Number(e.target.value))}
        required={required}
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
