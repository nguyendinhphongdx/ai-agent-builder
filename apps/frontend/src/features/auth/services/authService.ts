import { apiClient } from "@/lib/api/client";
import type {
  AuthResponse,
  ForgotPasswordInput,
  LoginInput,
  RegisterInput,
  ResetPasswordInput,
  User,
  VerifyEmailConfirmInput,
} from "../types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

/** Absolute URL for starting an OAuth flow.
 * Redirects happen at the browser level — cannot use axios. */
export function oauthStartUrl(
  provider: "github" | "google",
  redirectTo?: string,
): string {
  const base = `${API_BASE}/auth/oauth/${provider}/start`;
  const qs = redirectTo ? `?redirect_to=${encodeURIComponent(redirectTo)}` : "";
  return `${base}${qs}`;
}

export interface MfaChallenge {
  mfa_required: true;
  mfa_token: string;
}

/** Server-side login response is either AuthResponse (cookies set) or
 *  MfaChallenge (no cookies; needs second step). The discriminator
 *  is the ``mfa_required`` field — present + true means challenge. */
export type LoginResult = AuthResponse | MfaChallenge;

export function isMfaChallenge(r: LoginResult): r is MfaChallenge {
  return (r as MfaChallenge).mfa_required === true;
}

export const authService = {
  login: (data: LoginInput) =>
    apiClient.post<LoginResult>("/auth/login", data).then((r) => r.data),

  verifyMfaLogin: (data: {
    mfa_token: string;
    code: string;
    remember_me?: boolean;
  }) =>
    apiClient
      .post<AuthResponse>("/auth/mfa/verify-login", data)
      .then((r) => r.data),

  register: (data: RegisterInput) =>
    apiClient.post<AuthResponse>("/auth/register", data).then((r) => r.data),

  logout: () => apiClient.post("/auth/logout"),

  getMe: () => apiClient.get<User>("/auth/me").then((r) => r.data),

  updateMe: (data: { full_name?: string | null; avatar_url?: string | null }) =>
    apiClient.patch<User>("/auth/me", data).then((r) => r.data),

  uploadAvatar: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiClient
      .post<User>("/auth/me/avatar", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  changePassword: (data: { current_password: string; new_password: string }) =>
    apiClient.post<void>("/auth/me/password", data).then((r) => r.data),

  requestEmailChange: (data: { new_email: string; current_password: string }) =>
    apiClient
      .post<{ sent: true; to: string }>("/auth/me/email", data)
      .then((r) => r.data),

  confirmEmailChange: (data: { code: string }) =>
    apiClient
      .post<{ email: string }>("/auth/me/email/confirm", data)
      .then((r) => r.data),

  forgotPassword: (data: ForgotPasswordInput) =>
    apiClient.post<{ sent: true }>("/auth/forgot-password", data).then((r) => r.data),

  resetPassword: (data: ResetPasswordInput) =>
    apiClient.post<{ ok: true }>("/auth/reset-password", data).then((r) => r.data),

  verifyEmailConfirm: (data: VerifyEmailConfirmInput) =>
    apiClient.post<{ verified: true }>("/auth/verify-email/confirm", data).then((r) => r.data),

  verifyEmailResend: () =>
    apiClient.post<{ sent: true }>("/auth/verify-email/send").then((r) => r.data),
};
