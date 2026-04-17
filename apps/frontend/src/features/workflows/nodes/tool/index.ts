import { Wrench } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import ToolPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "tool",
  label: "Tool",
  description: "Execute a tool",
  icon: Wrench,
  color: "#f59e0b",
  category: "integration",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  configFields: [
    { key: "tool_id", label: "Tool", type: "select" as const, options: [] },
    { key: "input_mapping", label: "Input Mapping", type: "json" as const, placeholder: '{"query": "{user_input}"}' },
    { key: "output_variable", label: "Output Variable", type: "text" as const, placeholder: "tool_result" },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = ToolPanelComponent;
