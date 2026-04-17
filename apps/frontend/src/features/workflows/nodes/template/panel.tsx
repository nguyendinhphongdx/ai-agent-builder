import { TextField, TextareaField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function TemplatePanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <TextareaField
        label="Template"
        value={(config.template as string) || ""}
        onChange={(v) => updateConfig("template", v)}
        placeholder="Hello {{name}}, your order #{{order_id}} is ready."
      />
      <TextField
        label="Output Variable"
        value={(config.output_variable as string) || ""}
        onChange={(v) => updateConfig("output_variable", v)}
        placeholder="template_output"
      />
    </div>
  );
}
