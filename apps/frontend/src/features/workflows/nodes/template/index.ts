import { FileText } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import TemplatePanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "template",
  label: "Template",
  description: "Transform data with templates",
  icon: FileText,
  color: "#14b8a6",
  category: "data",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ template: "", output_variable: "template_output" }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = TemplatePanelComponent;
