import { useMemo } from "react";
import { SelectField } from "../../components/node-inspector/fields";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import { useAgents } from "@/features/agents/hooks/useAgents";
import type { PanelProps } from "../types";

const OUTPUT_MODE_OPTIONS = [
  { label: "Text only", value: "text" },
  { label: "Structured (response + tool results)", value: "structured" },
];

export default function AgentPanel({ id }: PanelProps) {
  const { config, updateConfig } = useNodeConfig(id);
  const { data: agents } = useAgents();

  const agentOptions = useMemo(
    () => (agents || []).map((a: { id: string; name: string }) => ({ label: a.name, value: a.id })),
    [agents]
  );

  return (
    <div className="space-y-4">
      <SelectField
        label="Agent"
        value={(config.agent_id as string) || ""}
        options={agentOptions}
        onChange={(v) => updateConfig("agent_id", v)}
      />
      <SelectField
        label="Output Mode"
        value={(config.output_mode as string) || "text"}
        options={OUTPUT_MODE_OPTIONS}
        onChange={(v) => updateConfig("output_mode", v)}
      />
    </div>
  );
}
