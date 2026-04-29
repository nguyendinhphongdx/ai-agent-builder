import { ExpressionField, TextField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function TemplatePanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <ExpressionField
        nodeId={id}
        label="Template"
        value={(config.template as string) || ""}
        onChange={(v) => updateConfig("template", v)}
        placeholder="Hello {{ json.name }}, your order #{{ json.order_id }} is ready."
        height={120}
        hint="Use {{ json.field }}, {{ items[0].x }}, {{ nodes['NodeLabel'][0].field }}, {{ vars.x }}."
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
