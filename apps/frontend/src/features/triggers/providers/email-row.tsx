"use client";

import { TriggerRowFrame } from "../components/TriggerRowFrame";
import type { TriggerRowProps } from "./types";

type EmailConfig = {
  imap_host?: string;
  imap_port?: number;
  imap_username?: string;
  imap_folder?: string;
  poll_interval_seconds?: number;
};

export function EmailRow({ item, onDelete }: TriggerRowProps) {
  const cfg = item.config as EmailConfig;
  return (
    <TriggerRowFrame
      name={item.name}
      active={item.is_active}
      lastError={item.last_error}
      onDelete={onDelete}
      summary={
        <>
          {cfg.imap_username}@{cfg.imap_host}:{cfg.imap_port} ·{" "}
          {cfg.imap_folder} · poll every {cfg.poll_interval_seconds}s
        </>
      }
    />
  );
}
