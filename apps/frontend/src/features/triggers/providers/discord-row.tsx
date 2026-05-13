"use client";

import { TriggerRowFrame } from "../components/TriggerRowFrame";
import type { TriggerRowProps } from "./types";

export function DiscordRow({ item, onDelete }: TriggerRowProps) {
  const cfg = item.config as {
    discord_application_id?: string;
    filter_command?: string;
  };
  return (
    <TriggerRowFrame
      name={item.name}
      active={item.is_active}
      lastError={item.last_error}
      onDelete={onDelete}
      summary={
        <>
          App {cfg.discord_application_id}
          {cfg.filter_command && ` · /${cfg.filter_command}`}
        </>
      }
    />
  );
}
