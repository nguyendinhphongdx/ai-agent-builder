import { TextField, TextareaField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

const LANGUAGE_OPTIONS = [
  { label: "Python", value: "python" },
  { label: "JavaScript", value: "javascript" },
];

export default function CodePanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <SelectField
        label="Language"
        value={(config.language as string) || "python"}
        options={LANGUAGE_OPTIONS}
        onChange={(v) => updateConfig("language", v)}
      />
      <TextareaField
        label="Code"
        value={(config.code as string) || ""}
        onChange={(v) => updateConfig("code", v)}
        placeholder="result = len(user_input.split())"
        mono
      />
      <TextField
        label="Output Variable"
        value={(config.output_variable as string) || ""}
        onChange={(v) => updateConfig("output_variable", v)}
        placeholder="code_result"
      />
    </div>
  );
}
