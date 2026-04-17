import { TextField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function EndPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <TextField
      label="Output Variable"
      value={(config.output_variable as string) || ""}
      onChange={(v) => updateConfig("output_variable", v)}
      placeholder="final_response"
    />
  );
}
