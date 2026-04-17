"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { MonacoEditor } from "../MonacoEditor";

const LANGUAGES = [
  { value: "python", label: "Python 3" },
  { value: "javascript", label: "JavaScript (Node.js)" },
] as const;
type Language = "python" | "javascript";

const DEFAULT_PYTHON = `# Access template variables via the 'inputs' dict
# Example: inputs['query'] -> user's query string

def run(inputs):
    query = inputs.get('query', '')
    # Your logic here
    result = f"Processed: {query}"
    return result
`;

const DEFAULT_JS = `// Access template variables via the 'inputs' object
// Example: inputs.query -> user's query string

function run(inputs) {
  const query = inputs.query || '';
  // Your logic here
  return \`Processed: \${query}\`;
}
`;

interface CodeConfig {
  language: Language;
  code_template: string;
}

function parseConfig(raw: Record<string, unknown>): CodeConfig {
  return {
    language: (raw.language as Language) ?? "python",
    code_template:
      (raw.code_template as string) ||
      (raw.language === "javascript" ? DEFAULT_JS : DEFAULT_PYTHON),
  };
}

interface CodeConfigFormProps {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

export function CodeConfigForm({ value, onChange }: CodeConfigFormProps) {
  const cfg = parseConfig(value);

  const update = (patch: Partial<CodeConfig>) => {
    const updated = { ...cfg, ...patch };
    onChange(updated);
  };

  return (
    <div className="space-y-3">
      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">Runtime language</Label>
        <Select
          value={cfg.language}
          onValueChange={(v) => {
            const lang = v as Language;
            const defaultCode = lang === "javascript" ? DEFAULT_JS : DEFAULT_PYTHON;
            update({ language: lang, code_template: defaultCode });
          }}
        >
          <SelectTrigger className="h-8 w-48 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LANGUAGES.map((l) => (
              <SelectItem key={l.value} value={l.value} className="text-xs">
                {l.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label className="text-xs text-muted-foreground">Code template</Label>
        <p className="text-[11px] text-muted-foreground">
          Template variables (e.g.{" "}
          <code className="rounded bg-muted px-1">{"{query}"}</code>) are injected via the{" "}
          <code className="rounded bg-muted px-1">inputs</code> dict at runtime.
        </p>
        <MonacoEditor
          language={cfg.language}
          height={360}
          value={cfg.code_template}
          onChange={(v) => update({ code_template: v })}
        />
      </div>
    </div>
  );
}

/* Variant for custom_function (simpler label) */
export function CustomFunctionConfigForm({ value, onChange }: CodeConfigFormProps) {
  const cfg = parseConfig({ language: "python", ...value });

  const update = (patch: Partial<{ function_code: string; language: Language }>) => {
    onChange({ ...cfg, ...patch, code_template: patch.function_code ?? (value.function_code as string ?? "") });
  };

  return (
    <div className="space-y-3">
      <p className="text-[11px] text-muted-foreground">
        Write a Python function that the LLM can call. Template variables are passed in via the{" "}
        <code className="rounded bg-muted px-1">inputs</code> argument.
      </p>
      <MonacoEditor
        language="python"
        height={360}
        value={(value.function_code as string) ?? DEFAULT_PYTHON}
        onChange={(v) => onChange({ ...value, function_code: v })}
      />
    </div>
  );
}
