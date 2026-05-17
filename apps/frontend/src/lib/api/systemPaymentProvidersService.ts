import { apiClient } from "./client";

/**
 * Admin surface for ``payment_provider_configs`` — Stripe / MoMo /
 * future gateways. Secrets are Fernet-encrypted server-side and never
 * returned in plaintext; the UI shows ``secrets_preview`` (masked).
 *
 * Edit semantics (mirrors the backend service):
 *   - send ``secrets: null``  → preserve existing secrets blob
 *     (admin only changed non-secret config or the enabled flag).
 *   - send ``secrets: {}``    → wipe all secrets.
 *   - send a populated dict   → replace the blob.
 */

export interface SystemPaymentProviderKey {
  key: string;
  label: string;
  hint?: string;
  is_set?: boolean;
}

export interface SystemPaymentProviderGuideSection {
  title: string;
  steps: string[];
}

export interface SystemPaymentProviderGuideWebhook {
  /** Path portion alone — useful when the operator wants to copy just
   *  the suffix and combine it with their own base. */
  path: string;
  /** Fully-qualified URL resolved server-side from settings.BASE_URL.
   *  This is what an admin should actually paste into the provider's
   *  dashboard. */
  url?: string;
  events: string[];
  note?: string;
}

export interface SystemPaymentProviderGuide {
  intro: string;
  requirements?: string[];
  webhook?: SystemPaymentProviderGuideWebhook | null;
  sections?: SystemPaymentProviderGuideSection[];
  tips?: string[];
  docs?: [string, string][];
}

export interface SystemPaymentProviderRow {
  code: string;
  display_name: string;
  kind: "free" | "paid" | "both";
  is_enabled: boolean;
  is_test_mode: boolean;
  /** False when the provider class exists in code but no DB row has
   *  been created yet — saving the editor form will upsert. */
  persisted: boolean;
  secrets_preview: Record<string, string>;
  secret_keys: SystemPaymentProviderKey[];
  config: Record<string, unknown>;
  config_keys: SystemPaymentProviderKey[];
  guide: SystemPaymentProviderGuide | null;
  last_tested_at: string | null;
  last_test_result: string | null;
}

export interface SystemPaymentProviderUpsert {
  display_name: string;
  kind: "free" | "paid" | "both";
  is_enabled: boolean;
  is_test_mode: boolean;
  secrets: Record<string, string> | null;
  config: Record<string, unknown> | null;
  description?: string | null;
}

export interface SystemPaymentProviderTestResult {
  ok: boolean;
  message: string;
}

export const systemPaymentProvidersService = {
  list: (): Promise<SystemPaymentProviderRow[]> =>
    apiClient
      .get<SystemPaymentProviderRow[]>("/system/payment-providers")
      .then((r) => r.data),

  get: (code: string): Promise<SystemPaymentProviderRow> =>
    apiClient
      .get<SystemPaymentProviderRow>(`/system/payment-providers/${code}`)
      .then((r) => r.data),

  upsert: (
    code: string,
    body: SystemPaymentProviderUpsert,
  ): Promise<SystemPaymentProviderRow> =>
    apiClient
      .put<SystemPaymentProviderRow>(`/system/payment-providers/${code}`, body)
      .then((r) => r.data),

  remove: (code: string): Promise<void> =>
    apiClient
      .delete(`/system/payment-providers/${code}`)
      .then(() => undefined),

  test: (code: string): Promise<SystemPaymentProviderTestResult> =>
    apiClient
      .post<SystemPaymentProviderTestResult>(
        `/system/payment-providers/${code}/test`,
      )
      .then((r) => r.data),
};
