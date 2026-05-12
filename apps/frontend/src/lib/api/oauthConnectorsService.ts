import { apiClient } from "./client";

/**
 * One-row response from ``GET /oauth-connectors/providers`` — tells
 * the FE which providers are wired on this deployment so the UI can
 * hide "Connect <X>" buttons for unconfigured providers (vs. showing
 * them and getting a 400 on click).
 */
export interface OAuthProviderItem {
  id: string;
  label: string;
  configured: boolean;
}

/**
 * One-row response from ``GET /oauth-connectors/connections``. Tokens
 * never leave the server — the FE only ever sees the connection id
 * (used as a handle when wiring KB connectors / agents to a stored
 * connection) plus metadata for the UI.
 */
export interface OAuthConnection {
  id: string;
  provider: string;
  account_label: string | null;
  external_account_id: string | null;
  scope: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export const oauthConnectorsService = {
  listProviders: (): Promise<OAuthProviderItem[]> =>
    apiClient
      .get<OAuthProviderItem[]>("/oauth-connectors/providers")
      .then((r) => r.data),

  listConnections: (): Promise<OAuthConnection[]> =>
    apiClient
      .get<OAuthConnection[]>("/oauth-connectors/connections")
      .then((r) => r.data),

  /** Kick off a 3-legged dance. The BE mints a state token, persists
   *  it (with workspace + user stamped on), and returns the provider
   *  authorize URL. The caller redirects the browser to it. */
  start: (
    provider: string,
    returnTo?: string,
  ): Promise<{ authorize_url: string }> =>
    apiClient
      .post<{ authorize_url: string }>(
        `/oauth-connectors/${provider}/start`,
        { return_to: returnTo ?? null },
      )
      .then((r) => r.data),

  remove: (connectionId: string): Promise<void> =>
    apiClient
      .delete(`/oauth-connectors/connections/${connectionId}`)
      .then(() => undefined),
};
