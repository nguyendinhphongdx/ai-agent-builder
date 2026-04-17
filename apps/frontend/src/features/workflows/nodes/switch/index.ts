import { Route } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import SwitchPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "switch",
  label: "Switch",
  description: "Route to different outputs based on rules",
  icon: Route,
  color: "#06b6d4",
  category: "logic",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [
      { id: "case_0", type: "conditional", label: "Case 1" },
      { id: "case_1", type: "conditional", label: "Case 2" },
      { id: "case_2", type: "conditional", label: "Case 3" },
      { id: "default_out", type: "conditional", label: "Default" },
    ],
  },
  defaultData: () => ({
    _customHandles: true,
    variable: "",
    cases: [
      { id: "case_0", value: "", label: "Case 1" },
      { id: "case_1", value: "", label: "Case 2" },
      { id: "case_2", value: "", label: "Case 3" },
    ],
  }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = SwitchPanelComponent;
