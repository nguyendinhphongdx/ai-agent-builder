import { Filter } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import FilterPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "filter",
  label: "Filter",
  description: "Keep only items that match conditions",
  icon: Filter,
  color: "#10b981",
  category: "logic",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [
      { id: "matched", type: "conditional", label: "Matched" },
      { id: "unmatched", type: "conditional", label: "Unmatched" },
    ],
  },
  defaultData: () => ({ expression: "" }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = FilterPanelComponent;
