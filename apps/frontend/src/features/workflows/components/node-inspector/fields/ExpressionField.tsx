import { ExpressionInput } from "../../ExpressionInput";

interface ExpressionFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  /** Multi-line by default — single-line for URL-shaped fields. */
  multiline?: boolean;
  height?: number;
  hint?: string;
  /** Node id this field belongs to — drives upstream-aware autocomplete. */
  nodeId?: string;
}

/**
 * Templated text field: reuses the same panel layout as TextField / TextareaField
 * but renders a Monaco-backed editor that highlights ``{{ ... }}`` blocks and
 * autocompletes against the upstream output schema.
 */
export function ExpressionField({
  label,
  value,
  onChange,
  placeholder,
  multiline = true,
  height = 100,
  hint,
  nodeId,
}: ExpressionFieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <ExpressionInput
        value={value}
        onChange={onChange}
        singleLine={!multiline}
        height={height}
        placeholder={placeholder}
        nodeId={nodeId}
      />
      {hint && <p className="text-[10px] text-muted-foreground/70">{hint}</p>}
    </div>
  );
}
