import { TextField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function SwitchPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <TextField
        label="Variable to match"
        value={(config.variable as string) || ""}
        onChange={(v) => updateConfig("variable", v)}
        placeholder="classification"
      />
      <p className="text-[10px] text-muted-foreground">
        Each output route matches a different value of the variable.
      </p>
    </div>
  );
}
