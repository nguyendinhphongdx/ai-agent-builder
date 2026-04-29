import { ExpressionField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function SetVariablePanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <ExpressionField
      nodeId={id}
      label="Assignments (JSON)"
      value={(config.assignments as string) || ""}
      onChange={(v) => updateConfig("assignments", v)}
      placeholder={'{"result": "{{ json.data }}", "count": 42}'}
      height={140}
      hint="Each value is an expression. Pure {{ expr }} preserves type (e.g. 42 stays an int)."
    />
  );
}
