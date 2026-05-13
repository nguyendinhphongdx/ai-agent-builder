"use client";

import { TriggerRowFrame } from "../components/TriggerRowFrame";
import type { TriggerRowProps } from "./types";

type SlackConfig = {
  slack_team_id?: string;
  filter_event_type?: string;
  filter_channel_id?: string;
  filter_command?: string;
  filter_keyword?: string;
};

export function SlackRow({ item, onDelete }: TriggerRowProps) {
  const cfg = item.config as SlackConfig;
  return (
    <TriggerRowFrame
      name={item.name}
      active={item.is_active}
      lastError={item.last_error}
      onDelete={onDelete}
      summary={
        <>
          {cfg.slack_team_id} · {cfg.filter_event_type}
          {cfg.filter_channel_id && ` · #${cfg.filter_channel_id}`}
          {cfg.filter_command && ` · ${cfg.filter_command}`}
          {cfg.filter_keyword && ` · contains "${cfg.filter_keyword}"`}
        </>
      }
    />
  );
}
