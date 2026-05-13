import { MessageCircle } from "lucide-react";
import { TeamsRow } from "./teams-row";
import { TeamsForm } from "./teams-form";
import type { TriggerProvider } from "./types";

export const teamsProvider: TriggerProvider = {
  type: "teams",
  label: "Microsoft Teams",
  icon: MessageCircle,
  cardTitle: "Microsoft Teams triggers",
  cardDescription:
    "Outgoing webhooks. Each trigger gets a unique URL — paste the HMAC secret Teams shows when you add the webhook.",
  emptyMessage: "No Teams triggers yet.",
  RowComponent: TeamsRow,
  FormComponent: TeamsForm,
};
