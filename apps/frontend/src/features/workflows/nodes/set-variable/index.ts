import { Variable } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import SetVariablePanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "set_variable",
  label: "Set Variable",
  description: "Set or transform variables",
  icon: Variable,
  color: "#6366f1",
  category: "data",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ assignments: "{}" }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = SetVariablePanelComponent;
