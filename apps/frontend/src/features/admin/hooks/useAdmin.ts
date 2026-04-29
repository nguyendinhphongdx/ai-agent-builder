"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminService } from "../services/adminService";
import type {
  GrantRoleInput,
  PayoutSuspendInput,
  TemplateModerationInput,
  UserBanInput,
} from "../types";

const adminKeys = {
  all: ["admin"] as const,
  templates: (params: object) => [...adminKeys.all, "templates", params] as const,
  users: (params: object) => [...adminKeys.all, "users", params] as const,
  purchases: (params: object) => [...adminKeys.all, "purchases", params] as const,
  stats: () => [...adminKeys.all, "stats"] as const,
  audit: (params: object) => [...adminKeys.all, "audit", params] as const,
};

// ─── Templates ────────────────────────────────────────────────────────

export function useAdminTemplates(params: { status?: string; q?: string } = {}) {
  return useQuery({
    queryKey: adminKeys.templates(params),
    queryFn: () => adminService.listTemplates(params),
    staleTime: 15_000,
  });
}

export function useModerateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: TemplateModerationInput }) =>
      adminService.moderateTemplate(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...adminKeys.all, "templates"] });
      queryClient.invalidateQueries({ queryKey: adminKeys.audit({}) });
    },
  });
}

// ─── Users ────────────────────────────────────────────────────────────

export function useAdminUsers(params: { q?: string } = {}) {
  return useQuery({
    queryKey: adminKeys.users(params),
    queryFn: () => adminService.listUsers(params),
    staleTime: 15_000,
  });
}

export function useBanUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: UserBanInput }) =>
      adminService.banUser(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...adminKeys.all, "users"] });
      queryClient.invalidateQueries({ queryKey: adminKeys.audit({}) });
    },
  });
}

export function useGrantRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: GrantRoleInput }) =>
      adminService.grantRole(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...adminKeys.all, "users"] });
      queryClient.invalidateQueries({ queryKey: adminKeys.audit({}) });
    },
  });
}

export function useSetPayoutStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: PayoutSuspendInput }) =>
      adminService.setPayoutStatus(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...adminKeys.all, "users"] });
      queryClient.invalidateQueries({ queryKey: adminKeys.audit({}) });
    },
  });
}

// ─── Purchases ────────────────────────────────────────────────────────

export function useAdminPurchases(params: { status?: string } = {}) {
  return useQuery({
    queryKey: adminKeys.purchases(params),
    queryFn: () => adminService.listPurchases(params),
    staleTime: 15_000,
  });
}

export function useRefundPurchase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      adminService.refundPurchase(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...adminKeys.all, "purchases"] });
      queryClient.invalidateQueries({ queryKey: adminKeys.audit({}) });
    },
  });
}

export function useSettlePurchase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, reference }: { id: string; reference?: string }) =>
      adminService.settlePurchase(id, reference),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [...adminKeys.all, "purchases"] });
      queryClient.invalidateQueries({ queryKey: adminKeys.audit({}) });
    },
  });
}

// ─── Stats + audit ────────────────────────────────────────────────────

export function useAdminStats() {
  return useQuery({
    queryKey: adminKeys.stats(),
    queryFn: adminService.stats,
    staleTime: 30_000,
  });
}

export function useAdminAudit(params: { limit?: number } = { limit: 100 }) {
  return useQuery({
    queryKey: adminKeys.audit(params),
    queryFn: () => adminService.audit(params),
    staleTime: 10_000,
  });
}
