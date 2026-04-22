import { Brain } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import { NodeConnectionTypes } from "../types";
import LLMPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "llm",
  label: "LLM Call",
  description: "Call a language model",
  icon: Brain,
  color: "#8b5cf6",
  category: "ai",
  handles: {
    inputs: [{ id: "main", type: NodeConnectionTypes.Main }],
    outputs: [
      { id: "default", type: NodeConnectionTypes.Main },
      // ★ Exposes this node as a Chat Model provider for Agent nodes.
      { id: "model", type: NodeConnectionTypes.AiLanguageModel },
    ],
  },
  defaultData: () => ({
    llm_provider: "openai",
    llm_model: "gpt-4o",
  }),
  configFields: [
    { key: "llm_provider", label: "Provider", type: "select" as const, options: [{ label: "OpenAI", value: "openai" }, { label: "Anthropic", value: "anthropic" }, { label: "Ollama", value: "ollama" }], defaultValue: "openai" },
    { key: "api_key", label: "API Key", type: "text" as const, placeholder: "sk-..." },
    { key: "llm_model", label: "Model", type: "select" as const, options: [{ label: "GPT-4o", value: "gpt-4o" }, { label: "GPT-4o Mini", value: "gpt-4o-mini" }, { label: "Claude Sonnet 4", value: "claude-sonnet-4-20250514" }], defaultValue: "gpt-4o" },
    { key: "system_prompt", label: "System Prompt", type: "textarea" as const, placeholder: "You are a helpful assistant..." },
    { key: "user_prompt_template", label: "Prompt Template", type: "textarea" as const, placeholder: "Process this: {input}" },
    { key: "output_variable", label: "Output Variable", type: "text" as const, placeholder: "llm_output" },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = LLMPanelComponent;
