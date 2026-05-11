import { apiClient } from "./client";

/* ─── Email ────────────────────────────────────────────────── */

export interface EmailTrigger {
  id: string;
  workflow_id: string;
  workspace_id: string;
  name: string;
  imap_host: string;
  imap_port: number;
  imap_use_ssl: boolean;
  imap_username: string;
  imap_folder: string;
  poll_interval_seconds: number;
  mark_seen: boolean;
  is_active: boolean;
  last_seen_uid: number | null;
  last_polled_at: string | null;
  last_error: string | null;
  last_error_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailTriggerCreatePayload {
  workflow_id: string;
  name: string;
  imap_host: string;
  imap_port?: number;
  imap_use_ssl?: boolean;
  imap_username: string;
  imap_password: string;
  imap_folder?: string;
  poll_interval_seconds?: number;
  mark_seen?: boolean;
  is_active?: boolean;
}

export const emailTriggersService = {
  list: (workflowId?: string): Promise<EmailTrigger[]> =>
    apiClient
      .get<EmailTrigger[]>("/email-triggers", { params: workflowId ? { workflow_id: workflowId } : {} })
      .then((r) => r.data),
  create: (payload: EmailTriggerCreatePayload): Promise<EmailTrigger> =>
    apiClient.post<EmailTrigger>("/email-triggers", payload).then((r) => r.data),
  remove: (id: string): Promise<void> =>
    apiClient.delete(`/email-triggers/${id}`).then(() => undefined),
  pollNow: (id: string) =>
    apiClient.post(`/email-triggers/${id}/poll-now`).then((r) => r.data),
};

/* ─── Slack ────────────────────────────────────────────────── */

export interface SlackTrigger {
  id: string;
  workflow_id: string;
  workspace_id: string;
  name: string;
  slack_team_id: string;
  filter_event_type: string;
  filter_channel_id: string | null;
  filter_command: string | null;
  filter_keyword: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SlackTriggerCreatePayload {
  workflow_id: string;
  name: string;
  slack_team_id: string;
  filter_event_type: string;
  filter_channel_id?: string | null;
  filter_command?: string | null;
  filter_keyword?: string | null;
  is_active?: boolean;
}

export const slackTriggersService = {
  list: (workflowId?: string): Promise<SlackTrigger[]> =>
    apiClient
      .get<SlackTrigger[]>("/slack-triggers", { params: workflowId ? { workflow_id: workflowId } : {} })
      .then((r) => r.data),
  create: (payload: SlackTriggerCreatePayload): Promise<SlackTrigger> =>
    apiClient.post<SlackTrigger>("/slack-triggers", payload).then((r) => r.data),
  remove: (id: string): Promise<void> =>
    apiClient.delete(`/slack-triggers/${id}`).then(() => undefined),
};

/* ─── Teams ────────────────────────────────────────────────── */

export interface TeamsTrigger {
  id: string;
  workflow_id: string;
  workspace_id: string;
  name: string;
  filter_keyword: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TeamsTriggerCreatePayload {
  workflow_id: string;
  name: string;
  hmac_secret: string;
  filter_keyword?: string | null;
  is_active?: boolean;
}

export const teamsTriggersService = {
  list: (workflowId?: string): Promise<TeamsTrigger[]> =>
    apiClient
      .get<TeamsTrigger[]>("/teams-triggers", { params: workflowId ? { workflow_id: workflowId } : {} })
      .then((r) => r.data),
  create: (payload: TeamsTriggerCreatePayload): Promise<TeamsTrigger> =>
    apiClient.post<TeamsTrigger>("/teams-triggers", payload).then((r) => r.data),
  remove: (id: string): Promise<void> =>
    apiClient.delete(`/teams-triggers/${id}`).then(() => undefined),
};

/* ─── Discord ──────────────────────────────────────────────── */

export interface DiscordTrigger {
  id: string;
  workflow_id: string;
  workspace_id: string;
  name: string;
  discord_application_id: string;
  discord_public_key: string;
  filter_command: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DiscordTriggerCreatePayload {
  workflow_id: string;
  name: string;
  discord_application_id: string;
  discord_public_key: string;
  filter_command?: string | null;
  is_active?: boolean;
}

export const discordTriggersService = {
  list: (workflowId?: string): Promise<DiscordTrigger[]> =>
    apiClient
      .get<DiscordTrigger[]>("/discord-triggers", { params: workflowId ? { workflow_id: workflowId } : {} })
      .then((r) => r.data),
  create: (payload: DiscordTriggerCreatePayload): Promise<DiscordTrigger> =>
    apiClient.post<DiscordTrigger>("/discord-triggers", payload).then((r) => r.data),
  remove: (id: string): Promise<void> =>
    apiClient.delete(`/discord-triggers/${id}`).then(() => undefined),
};
