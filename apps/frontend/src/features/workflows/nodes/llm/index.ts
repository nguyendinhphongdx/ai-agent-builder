import { Brain } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import { NodeConnectionTypes } from "../types";
import LLMPanelComponent from "./panel";

// Catalog-driven fields live in `panel.tsx` (uses useModelCatalog hook). The
// definition here only declares the shape — `PanelComponent` renders the
// actual inputs with live catalog data.
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
    model_id: "openai/gpt-4o",
    credential_id: null,
  }),
  configFields: [
    { key: "model_id", label: "Model", type: "text" as const, defaultValue: "openai/gpt-4o" },
    { key: "credential_id", label: "Credential ID", type: "text" as const },
    { key: "system_prompt", label: "System Prompt", type: "textarea" as const, placeholder: "You are a helpful assistant..." },
    { key: "user_prompt_template", label: "Prompt Template", type: "textarea" as const, placeholder: "Process this: {input}" },
    { key: "output_variable", label: "Output Variable", type: "text" as const, placeholder: "llm_output" },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = LLMPanelComponent;
