import { Merge } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import MergePanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "merge",
  label: "Merge",
  description: "Combine data from multiple branches",
  icon: Merge,
  color: "#f97316",
  category: "logic",
  handles: {
    inputs: [
      { id: "input_a", type: "main", label: "A" },
      { id: "input_b", type: "main", label: "B" },
    ],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ mode: "append" }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = MergePanelComponent;
