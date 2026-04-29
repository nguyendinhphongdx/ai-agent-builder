"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { authService } from "../services/authService";
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

export function useLogin() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: LoginInput) => authService.login(data),
    onSuccess: (res) => {
      queryClient.setQueryData(authKeys.me, res.user);
      router.push(res.user.is_verified ? "/home" : "/verify-email/pending");
    },
  });
}

export function useRegister() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (data: RegisterInput) => authService.register(data),
    onSuccess: (res) => {
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
