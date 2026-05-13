import { Hash } from "lucide-react";
import { DiscordRow } from "./discord-row";
import { DiscordForm } from "./discord-form";
import type { TriggerProvider } from "./types";

export const discordProvider: TriggerProvider = {
  type: "discord",
  label: "Discord",
  icon: Hash,
  cardTitle: "Discord triggers",
  cardDescription:
    "Slash-command interactions. Point your bot's Interactions Endpoint URL at /api/triggers/discord/interactions.",
  emptyMessage: "No Discord triggers yet.",
  RowComponent: DiscordRow,
  FormComponent: DiscordForm,
};
