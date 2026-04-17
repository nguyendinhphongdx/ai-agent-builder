import { User } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import HumanInputPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "human_input",
  label: "Human Input",
  description: "Wait for user input",
  icon: User,
  color: "#ec4899",
  category: "flow",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ timeout_seconds: 300 }),
  configFields: [
    { key: "prompt_message", label: "Prompt Message", type: "text" as const, placeholder: "Please provide more details:" },
    { key: "timeout_seconds", label: "Timeout (seconds)", type: "number" as const, defaultValue: 300 },
  ],
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = HumanInputPanelComponent;
