import { Repeat } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import LoopPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "loop",
  label: "Loop",
  description: "Iterate over items in batches",
  icon: Repeat,
  color: "#a855f7",
  category: "logic",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [
      { id: "loop_body", type: "conditional", label: "Loop body" },
      { id: "done", type: "conditional", label: "Done" },
    ],
  },
  defaultData: () => ({ batch_size: 1, max_iterations: 100 }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = LoopPanelComponent;
