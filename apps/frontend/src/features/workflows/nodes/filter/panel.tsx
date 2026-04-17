import { TextField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function FilterPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <TextField
      label="Filter Expression"
      value={(config.expression as string) || ""}
      onChange={(v) => updateConfig("expression", v)}
      placeholder="item.status == 'active'"
    />
  );
}
