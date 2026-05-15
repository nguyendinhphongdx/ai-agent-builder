"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { resetSession } from "@/lib/api/client";
import { authService, isMfaChallenge } from "../services/authService";
import type {
  ForgotPasswordInput,
  LoginInput,
  RegisterInput,
  ResetPasswordInput,
  VerifyEmailConfirmInput,
} from "../types";

export const authKeys = {
  me: ["auth", "me"] as const,
};

export function useAuth() {
  const { data: user, isLoading, error } = useQuery({
    queryKey: authKeys.me,
    queryFn: authService.getMe,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  return { user: user ?? null, isLoading, isAuthenticated: !!user, error };
}

/** Self-edit (PATCH /auth/me). On success the cached `useAuth()` user
 *  refreshes immediately — Header avatar/name reactively follow. */
export function useUpdateMe() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authService.updateMe,
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
    },
  });
}

/** Upload a new avatar file. Backend stores it via the configured
 *  storage backend (local / S3 / GCS) and returns the resolved URL on
 *  the User row, which we drop into the cache so the Header + Profile
 *  preview update without a refetch. */
export function useUploadAvatar() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authService.uploadAvatar,
    onSuccess: (user) => {
      queryClient.setQueryData(authKeys.me, user);
    },
  });
}

/** Self-change password while authenticated. Backend re-issues cookies
 *  in the same response so the active tab stays logged in. */
export function useChangePassword() {
  return useMutation({ mutationFn: authService.changePassword });
}

/** Step 1 — request a code emailed to the new address. Returns the
 *  target so the UI can confirm "code sent to …@example.com". */
export function useRequestEmailChange() {
  return useMutation({ mutationFn: authService.requestEmailChange });
}

/** Step 2 — submit the code. On success the cached user updates with
 *  the new email so Profile + Header reflect it immediately. */
export function useConfirmEmailChange() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: authService.confirmEmailChange,
    onSuccess: (data) => {
      // Patch the cached user — only the email changes.
      queryClient.setQueryData<{ email: string } | undefined>(
        authKeys.me,
        (prev) => (prev ? { ...prev, email: data.email } : prev),
      );
    },
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: LoginInput) => authService.login(data),
    onSuccess: (res) => {
      // MfaChallenge response — leave routing/UI to the caller (the
      // login form catches it and renders the second-step prompt).
      if (isMfaChallenge(res)) return;
      // Clear any sticky refresh-failure flag from a previous expired
      // session so the new cookies actually get exercised on 401s.
      resetSession();
      queryClient.setQueryData(authKeys.me, res.user);
      // Phase 2: post-login users hold a user_token (no workspace
      // claim yet). Route to /org so they explicitly pick a
      // workspace via the new enter-workspace flow. Unverified users
      // continue to the email-pending screen.
      router.push(res.user.is_verified ? "/org" : "/verify-email/pending");
    },
  });
}

export function useVerifyMfaLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: { mfa_token: string; code: string; remember_me?: boolean }) =>
      authService.verifyMfaLogin(data),
    onSuccess: (res) => {
      resetSession();
      queryClient.setQueryData(authKeys.me, res.user);
      router.push(res.user.is_verified ? "/org" : "/verify-email/pending");
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: RegisterInput) => authService.register(data),
    onSuccess: (res) => {
      resetSession();
      queryClient.setQueryData(authKeys.me, res.user);
      // Sau khi đăng ký thành công user đã logged in nhưng unverified —
      // đưa sang trang pending để họ biết phải check email.
      router.push("/verify-email/pending");
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: () => authService.logout(),
    onSuccess: () => {
      resetSession();
      queryClient.clear();
      router.push("/login");
    },
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (data: ForgotPasswordInput) => authService.forgotPassword(data),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (data: ResetPasswordInput) => authService.resetPassword(data),
  });
}

export function useVerifyEmailConfirm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: VerifyEmailConfirmInput) =>
      authService.verifyEmailConfirm(data),
    onSuccess: () => {
      // Invalidate /me so the unverified banner disappears.
      queryClient.invalidateQueries({ queryKey: authKeys.me });
    },
  });
}

export function useResendVerification() {
  return useMutation({
    mutationFn: () => authService.verifyEmailResend(),
  });
}
