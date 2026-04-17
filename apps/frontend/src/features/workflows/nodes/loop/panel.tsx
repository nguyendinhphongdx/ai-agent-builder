import { NumberField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

export default function LoopPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <NumberField
        label="Batch Size"
        value={config.batch_size as number | undefined}
        onChange={(v) => updateConfig("batch_size", v)}
        placeholder="1"
      />
      <NumberField
        label="Max Iterations"
        value={config.max_iterations as number | undefined}
        onChange={(v) => updateConfig("max_iterations", v)}
        placeholder="100"
      />
    </div>
  );
}
