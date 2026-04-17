import { Globe } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import HttpRequestPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "http_request",
  label: "HTTP Request",
  description: "Make HTTP API calls",
  icon: Globe,
  color: "#8b5cf6",
  category: "integration",
  handles: {
    inputs: [{ id: "default", type: "main" }],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({
    method: "GET",
    url: "",
    headers: "{}",
    body: "",
  }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = HttpRequestPanelComponent;
