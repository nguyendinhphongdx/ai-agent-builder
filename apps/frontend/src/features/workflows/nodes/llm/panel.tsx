import { useEffect, useState, useCallback, useMemo } from "react";
import {
  ExpressionField,
  SelectField,
  TextField,
} from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import {
  aiCredentialService,
  type AICredentialResponse,
} from "@/lib/api/aiCredentialService";
import {
  useModelCatalog,
  findProvider,
  providerOfModel,
} from "@/lib/models/catalog";
import type { PanelProps } from "../types";

export default function LLMPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);
  const { data: catalog } = useModelCatalog();
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

  const modelOptions = useMemo(
    () =>
      (catalog?.models ?? []).map((m) => ({
        label: `${m.name} (${findProvider(catalog?.providers, m.provider)?.label ?? m.provider})`,
        value: m.id,
      })),
    [catalog],
  );

  const provider = providerOfModel(modelId);
  const providerEntry = findProvider(catalog?.providers, provider);
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
        options={modelOptions}
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
          Chưa có credential cho {providerEntry?.label ?? provider}. Tạo trong
          trang Agent editor hoặc Settings.
        </p>
      )}
      <ExpressionField
        nodeId={id}
        label="System Prompt"
        value={(config.system_prompt as string) || ""}
        onChange={(v) => updateConfig("system_prompt", v)}
        placeholder="You are a helpful assistant..."
        height={80}
      />
      <ExpressionField
        nodeId={id}
        label="Prompt Template"
        value={(config.user_prompt_template as string) || ""}
        onChange={(v) => updateConfig("user_prompt_template", v)}
        placeholder="Process this: {{ json.input }}"
        height={120}
        hint="Reference upstream output via {{ nodes['NodeLabel'][0].field }}."
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
