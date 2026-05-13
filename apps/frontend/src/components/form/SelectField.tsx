"use client";

import { cn } from "@/lib/utils";

type SelectOption = { label: string; value: string };

type SelectFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
};

/**
 * Native `<select>` with the same look as TextField/NumberField.
 * Use when you need a basic dropdown inside dense forms (e.g. settings
 * panels). For rich pickers with search/filtering, use the radix
 * `<Select>` primitive from `components/ui/select` instead.
 */
export function SelectField({
  label,
  value,
  onChange,
  options,
  placeholder = "Select…",
  hint,
  error,
  required,
  disabled,
  className,
}: SelectFieldProps) {
  return (
    <label className={cn("block", className)}>
      <span className="mb-1 block text-[11px] font-medium text-muted-foreground">
        {label}
        {required && <span className="ml-0.5 text-destructive">*</span>}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
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
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error ? (
        <p className="mt-1 text-[10px] text-destructive">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-[10px] text-muted-foreground/70">{hint}</p>
      ) : null}
    </label>
  );
}
