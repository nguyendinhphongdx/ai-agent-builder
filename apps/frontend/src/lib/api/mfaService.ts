import { apiClient } from "./client";

export interface MfaStatus {
  mfa_enabled: boolean;
  has_totp_secret: boolean;
  backup_codes_remaining: number;
}

export interface TotpSetupResponse {
  secret: string;
  provisioning_uri: string;
}

export interface TotpVerifySetupResponse {
  enabled: boolean;
  backup_codes: string[];
}

export interface BackupCodesResponse {
  backup_codes: string[];
}

export const mfaService = {
  status: (): Promise<MfaStatus> =>
    apiClient.get<MfaStatus>("/auth/mfa/status").then((r) => r.data),

  setupTotp: (): Promise<TotpSetupResponse> =>
    apiClient
      .post<TotpSetupResponse>("/auth/mfa/totp/setup")
      .then((r) => r.data),

  verifySetupTotp: (code: string): Promise<TotpVerifySetupResponse> =>
    apiClient
      .post<TotpVerifySetupResponse>("/auth/mfa/totp/verify-setup", { code })
      .then((r) => r.data),

  regenerateBackupCodes: (): Promise<BackupCodesResponse> =>
    apiClient
      .post<BackupCodesResponse>("/auth/mfa/backup-codes/regenerate")
      .then((r) => r.data),

  disable: (code: string): Promise<void> =>
    apiClient
      .post("/auth/mfa/disable", { code })
      .then(() => undefined),
};
