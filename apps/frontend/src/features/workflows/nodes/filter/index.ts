import { Filter } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import { NodeConnectionTypes } from "../types";
import FilterPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "filter",
  label: "Filter",
  description: "Keep only items that match conditions",
  icon: Filter,
  color: "#10b981",
  category: "logic",
  handles: {
    inputs: [{ id: "default", type: NodeConnectionTypes.Main }],
    outputs: [
      { id: "matched", type: NodeConnectionTypes.Main, label: "Matched" },
      { id: "unmatched", type: NodeConnectionTypes.Main, label: "Unmatched" },
    ],
  },
  defaultData: () => ({ expression: "" }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = FilterPanelComponent;
