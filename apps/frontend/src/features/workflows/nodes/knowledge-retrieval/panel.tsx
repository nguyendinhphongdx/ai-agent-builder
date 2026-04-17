import { TextField, NumberField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function KnowledgeRetrievalPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <TextField
        label="Query Template"
        value={(config.query_template as string) || ""}
        onChange={(v) => updateConfig("query_template", v)}
        placeholder="{user_input}"
      />
      <NumberField
        label="Top K Results"
        value={config.top_k as number | undefined}
        onChange={(v) => updateConfig("top_k", v)}
        placeholder="5"
      />
      <TextField
        label="Output Variable"
        value={(config.output_variable as string) || ""}
        onChange={(v) => updateConfig("output_variable", v)}
        placeholder="retrieved_context"
      />
    </div>
  );
}
