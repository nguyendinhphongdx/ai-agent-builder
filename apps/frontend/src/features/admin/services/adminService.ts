import { apiClient } from "@/lib/api/client";
import type {
  AdminAction,
  AdminPurchaseRow,
  AdminStats,
  AdminTemplateRow,
  AdminUserRow,
  GrantRoleInput,
  PayoutSuspendInput,
  TemplateModerationInput,
  UserBanInput,
} from "../types";

export const adminService = {
  // Templates
  listTemplates: (params: { status?: string; q?: string; limit?: number; offset?: number } = {}) =>
    apiClient
      .get<AdminTemplateRow[]>("/admin/templates", { params })
      .then((r) => r.data),

  moderateTemplate: (id: string, body: TemplateModerationInput) =>
    apiClient
      .patch<AdminTemplateRow>(`/admin/templates/${id}`, body)
      .then((r) => r.data),

  // Users
  listUsers: (params: { q?: string; limit?: number; offset?: number } = {}) =>
    apiClient.get<AdminUserRow[]>("/admin/users", { params }).then((r) => r.data),

  banUser: (id: string, body: UserBanInput) =>
    apiClient
      .patch<AdminUserRow>(`/admin/users/${id}/ban`, body)
      .then((r) => r.data),

  grantRole: (id: string, body: GrantRoleInput) =>
    apiClient
      .patch<AdminUserRow>(`/admin/users/${id}/role`, body)
      .then((r) => r.data),

  setPayoutStatus: (id: string, body: PayoutSuspendInput) =>
    apiClient
      .patch<AdminUserRow>(`/admin/users/${id}/payouts`, body)
      .then((r) => r.data),

  // Purchases
  listPurchases: (params: { status?: string; limit?: number; offset?: number } = {}) =>
    apiClient
      .get<AdminPurchaseRow[]>("/admin/purchases", { params })
      .then((r) => r.data),

  refundPurchase: (id: string, reason?: string) =>
    apiClient
      .post<AdminPurchaseRow>(`/admin/purchases/${id}/refund`, { reason })
      .then((r) => r.data),

  settlePurchase: (id: string, reference?: string) =>
    apiClient
      .post<AdminPurchaseRow>(`/admin/purchases/${id}/settle`, { reference })
      .then((r) => r.data),

  // Stats + audit
  stats: () =>
    apiClient.get<AdminStats>("/admin/stats").then((r) => r.data),

  audit: (params: { limit?: number; offset?: number } = {}) =>
    apiClient.get<AdminAction[]>("/admin/audit", { params }).then((r) => r.data),
};
