import { Webhook } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import WebhookTriggerPanelComponent from "./panel";

export const definition: NodeTypeDefinition = {
  type: "webhook_trigger",
  label: "Webhook Trigger",
  description: "Start workflow on HTTP request",
  icon: Webhook,
  color: "#8b5cf6",
  category: "trigger",
  canDelete: false,
  shape: "rounded-l-full rounded-r-xl",
  handles: {
    inputs: [],
    outputs: [{ id: "default", type: "main" }],
  },
  defaultData: () => ({ method: "POST", path: "/webhook" }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = WebhookTriggerPanelComponent;
