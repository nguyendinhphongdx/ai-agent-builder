import { BookOpen } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import KnowledgePanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "knowledge_retrieval",
  label: "Knowledge Search",
  description: "Search knowledge base",
  icon: BookOpen,
  color: "#10b981",
  category: "data",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ top_k: 5 }),
  configFields: [
    { key: "query_template", label: "Query Template", type: "text" as const, placeholder: "{user_input}" },
    { key: "top_k", label: "Top K Results", type: "number" as const, defaultValue: 5 },
    { key: "output_variable", label: "Output Variable", type: "text" as const, placeholder: "retrieved_context" },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = KnowledgePanelComponent;
