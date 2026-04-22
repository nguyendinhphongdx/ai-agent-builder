import { Square } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import EndPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "end",
  label: "End",
  description: "Exit point of the workflow",
  icon: Square,
  color: "#ef4444",
  category: "flow",
  canDelete: false,
  shape: "rounded-r-full rounded-l-xl",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [],
  },
  defaultData: () => ({ output_variable: "final_response" }),
  configFields: [
    { key: "output_variable", label: "Output Variable", type: "text", placeholder: "final_response", defaultValue: "final_response" },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = EndPanelComponent;
