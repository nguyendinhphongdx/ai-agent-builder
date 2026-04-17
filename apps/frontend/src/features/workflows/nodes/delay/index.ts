import { Timer } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import DelayPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "delay",
  label: "Delay",
  description: "Wait before continuing",
  icon: Timer,
  color: "#f59e0b",
  category: "logic",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ delay_seconds: 5, unit: "seconds" }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = DelayPanelComponent;
