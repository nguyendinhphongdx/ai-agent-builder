import { NumberField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

const UNIT_OPTIONS = [
  { label: "Seconds", value: "seconds" },
  { label: "Minutes", value: "minutes" },
  { label: "Hours", value: "hours" },
];

export default function DelayPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <NumberField
        label="Duration"
        value={config.delay_seconds as number | undefined}
        onChange={(v) => updateConfig("delay_seconds", v)}
        placeholder="5"
      />
      <SelectField
        label="Unit"
        value={(config.unit as string) || "seconds"}
        options={UNIT_OPTIONS}
        onChange={(v) => updateConfig("unit", v)}
      />
    </div>
  );
}
