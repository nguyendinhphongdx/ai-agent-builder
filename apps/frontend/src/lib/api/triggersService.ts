import { apiClient } from "./client";

/**
 * Unified trigger API client — mirrors the backend ``/api/triggers``
 * router (one polymorphic table with ``type`` discriminator + JSONB
 * ``config`` per provider).
 *
 * Backend reference:
 *   * GET    /api/triggers              ?type= &workflow_id=
 *   * POST   /api/triggers              { type, workflow_id, name, config, credentials? }
 *   * GET    /api/triggers/{id}
 *   * PATCH  /api/triggers/{id}         partial update
 *   * DELETE /api/triggers/{id}
 *   * GET    /api/triggers/types        picker metadata
 *
 * The per-type config + credentials shapes live in the backend's
 * ``modules/runtime/triggers/schemas.py`` — keep these TS types in
 * sync when the contract changes.
 */

export type TriggerType = "slack" | "teams" | "discord" | "email" | "scheduled";

export interface Trigger {
  id: string;
  type: TriggerType;
  workflow_id: string;
  name: string;
  config: Record<string, unknown>;
  is_active: boolean;
  last_fired_at: string | null;
  last_error: string | null;
  next_run_at: string | null;
  last_polled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TriggerCreatePayload {
  type: TriggerType;
  workflow_id: string;
  name: string;
  config: Record<string, unknown>;
  credentials?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface TriggerUpdatePayload {
  name?: string;
  config?: Record<string, unknown>;
  credentials?: Record<string, unknown> | null;
  is_active?: boolean;
}

export interface TriggerTypeMeta {
  type: TriggerType;
  label: string;
  needs_credentials: boolean;
}

export const triggersService = {
  list: (params: { type?: TriggerType; workflow_id?: string } = {}): Promise<Trigger[]> =>
    apiClient
      .get<Trigger[]>("/triggers", {
        params: {
          ...(params.type ? { type: params.type } : {}),
          ...(params.workflow_id ? { workflow_id: params.workflow_id } : {}),
        },
      })
      .then((r) => r.data),

  knownTypes: (): Promise<TriggerTypeMeta[]> =>
    apiClient.get<TriggerTypeMeta[]>("/triggers/types").then((r) => r.data),

  get: (id: string): Promise<Trigger> =>
    apiClient.get<Trigger>(`/triggers/${id}`).then((r) => r.data),

  create: (payload: TriggerCreatePayload): Promise<Trigger> =>
    apiClient.post<Trigger>("/triggers", payload).then((r) => r.data),

  update: (id: string, payload: TriggerUpdatePayload): Promise<Trigger> =>
    apiClient.patch<Trigger>(`/triggers/${id}`, payload).then((r) => r.data),

  remove: (id: string): Promise<void> =>
    apiClient.delete(`/triggers/${id}`).then(() => undefined),
};


// ─── Per-type config / credential helpers ────────────────────────
// Convenience builders that produce the right ``config`` /
// ``credentials`` shape for the unified create endpoint. Keep these
// aligned with backend ``schemas.py``.

export function buildSlackPayload(input: {
  workflow_id: string;
  name: string;
  slack_team_id: string;
  filter_event_type: "app_mention" | "message" | "slash_command";
  filter_channel_id?: string;
  filter_command?: string;
  filter_keyword?: string;
}): TriggerCreatePayload {
  return {
    type: "slack",
    workflow_id: input.workflow_id,
    name: input.name,
    config: {
      slack_team_id: input.slack_team_id,
      filter_event_type: input.filter_event_type,
      ...(input.filter_channel_id ? { filter_channel_id: input.filter_channel_id } : {}),
      ...(input.filter_command ? { filter_command: input.filter_command } : {}),
      ...(input.filter_keyword ? { filter_keyword: input.filter_keyword } : {}),
    },
  };
}

export function buildTeamsPayload(input: {
  workflow_id: string;
  name: string;
  hmac_secret_b64: string;
  filter_keyword?: string;
}): TriggerCreatePayload {
  return {
    type: "teams",
    workflow_id: input.workflow_id,
    name: input.name,
    config: input.filter_keyword ? { filter_keyword: input.filter_keyword } : {},
    credentials: { hmac_secret_b64: input.hmac_secret_b64 },
  };
}

export function buildDiscordPayload(input: {
  workflow_id: string;
  name: string;
  discord_application_id: string;
  discord_public_key: string;
  filter_command?: string;
}): TriggerCreatePayload {
  return {
    type: "discord",
    workflow_id: input.workflow_id,
    name: input.name,
    config: {
      discord_application_id: input.discord_application_id,
      discord_public_key: input.discord_public_key,
      ...(input.filter_command ? { filter_command: input.filter_command } : {}),
    },
  };
}

export function buildEmailPayload(input: {
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
}): TriggerCreatePayload {
  return {
    type: "email",
    workflow_id: input.workflow_id,
    name: input.name,
    config: {
      imap_host: input.imap_host,
      imap_port: input.imap_port ?? 993,
      imap_use_ssl: input.imap_use_ssl ?? true,
      imap_username: input.imap_username,
      imap_folder: input.imap_folder ?? "INBOX",
      poll_interval_seconds: input.poll_interval_seconds ?? 300,
      mark_seen: input.mark_seen ?? true,
    },
    credentials: { imap_password: input.imap_password },
  };
}
