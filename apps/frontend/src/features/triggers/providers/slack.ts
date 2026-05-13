import { MessageCircle } from "lucide-react";
import { SlackRow } from "./slack-row";
import { SlackForm } from "./slack-form";
import type { TriggerProvider } from "./types";

export const slackProvider: TriggerProvider = {
  type: "slack",
  label: "Slack",
  icon: MessageCircle,
  cardTitle: "Slack triggers",
  cardDescription:
    "App mentions, channel messages, slash commands. Point your Slack app's Event URL at /api/triggers/slack/events.",
  emptyMessage: "No Slack triggers yet.",
  RowComponent: SlackRow,
  FormComponent: SlackForm,
};
