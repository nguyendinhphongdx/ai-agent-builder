import { apiClient } from "./client";

/** Coarse-grained scope catalogue — keep in sync with backend
 *  ``ALLOWED_SCOPES`` in app/personal_tokens/schemas.py. */
export const PERSONAL_TOKEN_SCOPES = [
  { value: "agents:read", label: "Read agents", group: "Agents" },
  { value: "agents:chat", label: "Chat with agents", group: "Agents" },
  { value: "conversations:read", label: "Read conversations", group: "Conversations" },
  { value: "conversations:write", label: "Create/modify conversations", group: "Conversations" },
  { value: "knowledge:read", label: "Read knowledge bases", group: "Knowledge" },
  { value: "workflows:read", label: "Read workflows", group: "Workflows" },
  { value: "workflows:execute", label: "Execute workflows", group: "Workflows" },
] as const;

export type PersonalTokenScope = (typeof PERSONAL_TOKEN_SCOPES)[number]["value"];

export interface PersonalToken {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface PersonalTokenCreated extends PersonalToken {
  /** Plaintext value — returned ONLY at creation. UI must show once + drop. */
  plaintext: string;
}

export interface PersonalTokenCreatePayload {
  name: string;
  scopes: string[];
  expires_at?: string | null;
}

export const personalTokenService = {
  list: () =>
    apiClient.get<PersonalToken[]>("/api-tokens").then((r) => r.data),

  create: (data: PersonalTokenCreatePayload) =>
    apiClient.post<PersonalTokenCreated>("/api-tokens", data).then((r) => r.data),

  revoke: (id: string) =>
    apiClient.post(`/api-tokens/${id}/revoke`).then(() => undefined),
};
