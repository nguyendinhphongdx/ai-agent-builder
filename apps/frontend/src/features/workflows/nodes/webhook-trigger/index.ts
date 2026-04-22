import { Webhook } from "lucide-react";
import type { NodeTypeDefinition, NodeContentProps } from "../types";
import { NodeConnectionTypes } from "../types";
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
    outputs: [{ id: "default", type: NodeConnectionTypes.Main }],
  },
  defaultData: () => ({
    method: "POST",
    path: "/webhook",
    response_mode: "immediately",
    response_code: 200,
    response_data: "",
  }),
};

export function NodeComponent(_props: NodeContentProps) {
  return null;
}

export const PanelComponent = WebhookTriggerPanelComponent;
