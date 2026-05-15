import { apiClient } from "./client";

/**
 * Org-security API client — SSO / SAML config, SCIM bearer tokens, and
 * per-workspace IP allowlists.
 *
 * Mirrors:
 *   apps/backend/app/modules/identity/auth/sso/router.py
 *
 * The Hub's /org/security tab is the only consumer. Endpoints live
 * under three distinct prefixes (orgs/, workspaces/) to mirror the
 * resource hierarchy on the BE — SSO + SCIM are org-scoped, IP rules
 * are workspace-scoped.
 */

// ─── SSO config ───────────────────────────────────────────────────

export type SSOProvider = "oidc" | "saml";

export interface SSOConfig {
  id: string;
  organization_id: string;
  provider: SSOProvider;
  display_name: string;
  is_active: boolean;
  default_role: string;
  jit_provisioning: boolean;
  attribute_mapping: Record<string, unknown>;
  // OIDC public fields — secret is never returned.
  oidc_issuer: string | null;
  oidc_client_id: string | null;
  oidc_scopes: string[];
  // SAML public fields.
  saml_idp_entity_id: string | null;
  saml_idp_sso_url: string | null;
  saml_sp_entity_id: string | null;
}

export interface SSOConfigPayload {
  provider: SSOProvider;
  display_name: string;
  is_active?: boolean;
  default_role?: string;
  jit_provisioning?: boolean;
  attribute_mapping?: Record<string, unknown>;
  oidc_issuer?: string | null;
  oidc_client_id?: string | null;
  /** Plaintext — encrypted server-side before persisting. Omit to
   *  keep the existing secret unchanged. */
  oidc_client_secret?: string | null;
  oidc_scopes?: string[] | null;
  saml_idp_entity_id?: string | null;
  saml_idp_sso_url?: string | null;
  saml_idp_x509_cert?: string | null;
  saml_sp_entity_id?: string | null;
}

// ─── SCIM tokens ──────────────────────────────────────────────────

export interface SCIMToken {
  id: string;
  name: string;
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export interface SCIMTokenCreated extends SCIMToken {
  /** Only returned at mint time. */
  plaintext: string;
}

// ─── IP rules ─────────────────────────────────────────────────────

export interface IPRule {
  id: string;
  workspace_id: string;
  cidr: string;
  description: string | null;
  created_at: string;
}

export const securityService = {
  // ── SSO config (org-scoped) ─────────────────────────────────────
  listSSOConfigs: (orgId: string): Promise<SSOConfig[]> =>
    apiClient.get<SSOConfig[]>(`/orgs/${orgId}/sso`).then((r) => r.data),

  /** Idempotent upsert keyed by ``(org_id, provider)``. */
  upsertSSOConfig: (orgId: string, body: SSOConfigPayload): Promise<SSOConfig> =>
    apiClient.put<SSOConfig>(`/orgs/${orgId}/sso`, body).then((r) => r.data),

  deleteSSOConfig: (orgId: string, provider: SSOProvider): Promise<void> =>
    apiClient.delete(`/orgs/${orgId}/sso/${provider}`).then(() => undefined),

  // ── SCIM tokens (org-scoped) ────────────────────────────────────
  listSCIMTokens: (orgId: string): Promise<SCIMToken[]> =>
    apiClient
      .get<SCIMToken[]>(`/orgs/${orgId}/scim-tokens`)
      .then((r) => r.data),

  createSCIMToken: (
    orgId: string,
    body: { name: string; expires_at?: string | null },
  ): Promise<SCIMTokenCreated> =>
    apiClient
      .post<SCIMTokenCreated>(`/orgs/${orgId}/scim-tokens`, body)
      .then((r) => r.data),

  revokeSCIMToken: (orgId: string, tokenId: string): Promise<void> =>
    apiClient
      .delete(`/orgs/${orgId}/scim-tokens/${tokenId}`)
      .then(() => undefined),

  // ── Workspace IP rules ──────────────────────────────────────────
  listIPRules: (workspaceId: string): Promise<IPRule[]> =>
    apiClient
      .get<IPRule[]>(`/workspaces/${workspaceId}/ip-rules`)
      .then((r) => r.data),

  createIPRule: (
    workspaceId: string,
    body: { cidr: string; description?: string | null },
  ): Promise<IPRule> =>
    apiClient
      .post<IPRule>(`/workspaces/${workspaceId}/ip-rules`, body)
      .then((r) => r.data),

  deleteIPRule: (workspaceId: string, ruleId: string): Promise<void> =>
    apiClient
      .delete(`/workspaces/${workspaceId}/ip-rules/${ruleId}`)
      .then(() => undefined),
};
