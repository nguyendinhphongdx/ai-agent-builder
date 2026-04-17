import { TextField, TextareaField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

const METHOD_OPTIONS = [
  { label: "GET", value: "GET" },
  { label: "POST", value: "POST" },
  { label: "PUT", value: "PUT" },
  { label: "PATCH", value: "PATCH" },
  { label: "DELETE", value: "DELETE" },
];

export default function HttpRequestPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);

  return (
    <div className="space-y-4">
      <SelectField
        label="Method"
        value={(config.method as string) || "GET"}
        options={METHOD_OPTIONS}
        onChange={(v) => updateConfig("method", v)}
      />
      <TextField
        label="URL"
        value={(config.url as string) || ""}
        onChange={(v) => updateConfig("url", v)}
        placeholder="https://api.example.com/data"
      />
      <TextareaField
        label="Headers (JSON)"
        value={(config.headers as string) || ""}
        onChange={(v) => updateConfig("headers", v)}
        placeholder='{"Authorization": "Bearer ..."}'
        mono
      />
      <TextareaField
        label="Body"
        value={(config.body as string) || ""}
        onChange={(v) => updateConfig("body", v)}
        placeholder='{"key": "value"}'
        mono
      />
      <TextField
        label="Output Variable"
        value={(config.output_variable as string) || ""}
        onChange={(v) => updateConfig("output_variable", v)}
        placeholder="http_response"
      />
    </div>
  );
}
