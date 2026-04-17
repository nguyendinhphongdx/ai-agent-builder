import { TextareaField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function SetVariablePanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <TextareaField
      label="Assignments (JSON)"
      value={(config.assignments as string) || ""}
      onChange={(v) => updateConfig("assignments", v)}
      placeholder='{"result": "{{input.data}}", "count": 42}'
      mono
    />
  );
}
