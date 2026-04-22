import { useEffect, useState, useCallback } from "react";
import { TextField, TextareaField, SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import {
  aiCredentialService,
  type AICredentialResponse,
} from "@/lib/api/aiCredentialService";
import {
  MODEL_CATALOG,
  getProvider,
  providerOfModel,
} from "@/lib/models/catalog";
import type { PanelProps } from "../types";

const MODEL_OPTIONS = MODEL_CATALOG.map((m) => ({
  label: `${m.name} (${getProvider(m.provider)?.label ?? m.provider})`,
  value: m.id,
}));

export default function LLMPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);
  const modelId = (config.model_id as string) || "openai/gpt-4o";
  const credentialId = (config.credential_id as string) || "";

  const [credentials, setCredentials] = useState<AICredentialResponse[]>([]);

  const load = useCallback(async () => {
    try {
      const list = await aiCredentialService.list();
      setCredentials(list);
    } catch {
      setCredentials([]);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const provider = providerOfModel(modelId);
  const credentialsForProvider = credentials.filter((c) => c.provider === provider);
  const credentialOptions = [
    { label: "— Select credential —", value: "" },
    ...credentialsForProvider.map((c) => ({
      label: `${c.name} (${c.masked_key})`,
      value: c.id,
    })),
  ];

  return (
    <div className="space-y-4">
      <SelectField
        label="Model"
        value={modelId}
        options={MODEL_OPTIONS}
        onChange={(v) => updateConfig("model_id", v)}
      />
      <SelectField
        label="Credential"
        value={credentialId}
        options={credentialOptions}
        onChange={(v) => updateConfig("credential_id", v)}
      />
      {credentialsForProvider.length === 0 && (
        <p className="text-[11px] text-muted-foreground">
          Chưa có credential cho {getProvider(provider)?.label ?? provider}. Tạo trong
          trang Agent editor hoặc Settings.
        </p>
      )}
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
