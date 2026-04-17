import { TextField, NumberField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function HumanInputPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <TextField
        label="Prompt Message"
        value={(config.prompt_message as string) || ""}
        onChange={(v) => updateConfig("prompt_message", v)}
        placeholder="Please provide more details:"
      />
      <NumberField
        label="Timeout (seconds)"
        value={config.timeout_seconds as number | undefined}
        onChange={(v) => updateConfig("timeout_seconds", v)}
        placeholder="300"
      />
    </div>
  );
}
