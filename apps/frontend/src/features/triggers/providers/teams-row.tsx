"use client";

import { TriggerRowFrame } from "../components/TriggerRowFrame";
import type { TriggerRowProps } from "./types";

export function TeamsRow({ item, onDelete }: TriggerRowProps) {
  const cfg = item.config as { filter_keyword?: string };
  return (
    <TriggerRowFrame
      name={item.name}
      active={item.is_active}
      lastError={item.last_error}
      onDelete={onDelete}
      summary={
        <>
          Webhook URL: /api/triggers/teams/{item.id}/events
          {cfg.filter_keyword && ` · contains "${cfg.filter_keyword}"`}
        </>
      }
    />
  );
}
