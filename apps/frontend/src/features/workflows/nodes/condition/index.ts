import { GitBranch } from "lucide-react";
import type { NodeTypeDefinition } from "../types";
import { NodeConnectionTypes } from "../types";
import ConditionNodeComponent from "./node";
import ConditionPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "condition",
  label: "Condition",
  description: "Branch based on a condition",
  icon: GitBranch,
  color: "#06b6d4",
  category: "logic",
  handles: {
    inputs: [{ id: "default", type: NodeConnectionTypes.Main }],
    outputs: [
      { id: "true", type: NodeConnectionTypes.Main, label: "True" },
      { id: "false", type: NodeConnectionTypes.Main, label: "False" },
    ],
  },
  defaultData: () => ({
    _customHandles: true,
    cases: [
      { id: "true", label: "True" },
      { id: "false", label: "False" },
    ],
  }),
  configFields: [
    { key: "expression", label: "Condition Expression", type: "text" as const, placeholder: "classification == 'billing'" },
  ],
};

export const NodeComponent = ConditionNodeComponent;

export const PanelComponent = ConditionPanelComponent;
