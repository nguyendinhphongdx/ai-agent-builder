import { useMemo } from "react";
import { TextField, TextareaField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import { useTools } from "@/features/tools/hooks/useTools";
import type { PanelProps } from "../types";

export default function ToolPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);
  const { data: tools } = useTools();

  const toolOptions = useMemo(
    () => (tools || []).map((t: { id: string; name: string }) => ({ label: t.name, value: t.id })),
    [tools]
  );

  return (
    <div className="space-y-4">
      <SelectField
        label="Tool"
        value={(config.tool_id as string) || ""}
        options={toolOptions}
        onChange={(v) => updateConfig("tool_id", v)}
      />
      <TextareaField
        label="Input Mapping"
        value={(config.input_mapping as string) || ""}
        onChange={(v) => updateConfig("input_mapping", v)}
        placeholder='{"query": "{user_input}"}'
        mono
      />
      <TextField
        label="Output Variable"
        value={(config.output_variable as string) || ""}
        onChange={(v) => updateConfig("output_variable", v)}
        placeholder="tool_result"
      />
    </div>
  );
}
