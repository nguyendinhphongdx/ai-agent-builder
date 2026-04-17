import { TextField, TextareaField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { PanelProps } from "../types";

const PROVIDER_OPTIONS = [
  { label: "OpenAI", value: "openai" },
  { label: "Anthropic", value: "anthropic" },
  { label: "Ollama", value: "ollama" },
];

const MODEL_OPTIONS: Record<string, { label: string; value: string }[]> = {
  openai: [
    { label: "GPT-4o", value: "gpt-4o" },
    { label: "GPT-4o Mini", value: "gpt-4o-mini" },
  ],
  anthropic: [
    { label: "Claude Sonnet 4", value: "claude-sonnet-4-20250514" },
  ],
  ollama: [
    { label: "Llama 3", value: "llama3" },
  ],
};

export default function LLMPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);
  const provider = (config.llm_provider as string) || "openai";

  return (
    <div className="space-y-4">
      <SelectField
        label="Provider"
        value={provider}
        options={PROVIDER_OPTIONS}
        onChange={(v) => updateConfig("llm_provider", v)}
      />
      <TextField
        label="API Key"
        value={(config.api_key as string) || ""}
        onChange={(v) => updateConfig("api_key", v)}
        placeholder="sk-..."
      />
      <SelectField
        label="Model"
        value={(config.llm_model as string) || ""}
        options={MODEL_OPTIONS[provider] || MODEL_OPTIONS.openai}
        onChange={(v) => updateConfig("llm_model", v)}
      />
      <TextareaField
        label="System Prompt"
        value={(config.system_prompt as string) || ""}
        onChange={(v) => updateConfig("system_prompt", v)}
        placeholder="You are a helpful assistant..."
      />
      <TextareaField
        label="Prompt Template"
        value={(config.user_prompt_template as string) || ""}
        onChange={(v) => updateConfig("user_prompt_template", v)}
        placeholder="Process this: {input}"
      />
      <TextField
        label="Output Variable"
        value={(config.output_variable as string) || ""}
        onChange={(v) => updateConfig("output_variable", v)}
        placeholder="llm_output"
      />
    </div>
  );
}
