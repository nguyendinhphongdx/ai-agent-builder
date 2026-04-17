import { Code } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import CodePanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "code",
  label: "Code",
  description: "Execute custom code",
  icon: Code,
  color: "#64748b",
  category: "data",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ language: "python" }),
  configFields: [
    { key: "language", label: "Language", type: "select" as const, options: [{ label: "Python", value: "python" }, { label: "JavaScript", value: "javascript" }], defaultValue: "python" },
    { key: "code", label: "Code", type: "textarea" as const, placeholder: "result = len(user_input.split())" },
    { key: "output_variable", label: "Output Variable", type: "text" as const, placeholder: "code_result" },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = CodePanelComponent;
