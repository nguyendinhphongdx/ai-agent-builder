import { Bot } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import { NodeConnectionTypes } from "../types";
import AgentPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "agent",
  label: "Agent",
  description: "Run a pre-built agent",
  icon: Bot,
  color: "#6366f1",
  category: "ai",
  handles: {
    inputs: [
      { id: "default", type: NodeConnectionTypes.Main },
      {
        id: "model",
        type: NodeConnectionTypes.AiLanguageModel,
        label: "Chat Model",
        required: true,
        maxConnections: 1,
      },
      {
        id: "memory",
        type: NodeConnectionTypes.AiMemory,
        label: "Memory",
        maxConnections: 1,
      },
      {
        id: "tool",
        type: NodeConnectionTypes.AiTool,
        label: "Tool",
      },
    ],
    outputs: [{ id: "main", type: NodeConnectionTypes.Main }],
  },
  defaultData: () => ({ output_mode: "text" }),
  configFields: [
    { key: "agent_id", label: "Agent", type: "select" as const, options: [] },
    {
      key: "output_mode",
      label: "Output Mode",
      type: "select" as const,
      options: [
        { label: "Text only", value: "text" },
        { label: "Structured (response + tool results)", value: "structured" },
      ],
      defaultValue: "text",
    },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = AgentPanelComponent;
