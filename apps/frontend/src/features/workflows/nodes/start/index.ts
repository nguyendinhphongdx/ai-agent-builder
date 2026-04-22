import { Play } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import StartPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "start",
  label: "Start",
  description: "Entry point of the workflow",
  icon: Play,
  color: "#10b981",
  category: "flow",
  canDelete: false,
  shape: "rounded-l-full rounded-r-xl",
  handles: {
    inputs: [],
    outputs: [{ id: "default", type: "main" }],
  },
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = StartPanelComponent;
