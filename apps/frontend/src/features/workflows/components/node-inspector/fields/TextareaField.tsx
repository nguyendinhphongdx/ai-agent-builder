import { Textarea } from "@/components/ui/textarea";

interface TextareaFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  mono?: boolean;
}

export function TextareaField({ label, value, onChange, placeholder, mono = false }: TextareaFieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <Textarea
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={`min-h-20 text-xs ${mono ? "font-mono" : ""}`}
      />
    </div>
  );
}
