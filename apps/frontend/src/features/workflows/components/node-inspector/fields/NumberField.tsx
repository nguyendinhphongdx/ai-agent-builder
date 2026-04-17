import { Input } from "@/components/ui/input";

interface NumberFieldProps {
  label: string;
  value: number | undefined;
  onChange: (value: number) => void;
  placeholder?: string;
}

export function NumberField({ label, value, onChange, placeholder }: NumberFieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <Input
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
        placeholder={placeholder}
      />
    </div>
  );
}
