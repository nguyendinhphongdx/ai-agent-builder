import { TextField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

const METHOD_OPTIONS = [
  { label: "POST", value: "POST" },
  { label: "GET", value: "GET" },
  { label: "PUT", value: "PUT" },
];

export default function WebhookTriggerPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <SelectField
        label="HTTP Method"
        value={(config.method as string) || "POST"}
        options={METHOD_OPTIONS}
        onChange={(v) => updateConfig("method", v)}
      />
      <TextField
        label="Path"
        value={(config.path as string) || ""}
        onChange={(v) => updateConfig("path", v)}
        placeholder="/webhook"
      />
    </div>
  );
}
