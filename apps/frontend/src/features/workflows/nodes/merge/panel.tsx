import { SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

const MODE_OPTIONS = [
  { label: "Append", value: "append" },
  { label: "Combine by position", value: "combine_position" },
  { label: "Combine by field", value: "combine_field" },
  { label: "Keep only matches", value: "inner_join" },
];

export default function MergePanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <SelectField
      label="Mode"
      value={(config.mode as string) || "append"}
      options={MODE_OPTIONS}
      onChange={(v) => updateConfig("mode", v)}
    />
  );
}
