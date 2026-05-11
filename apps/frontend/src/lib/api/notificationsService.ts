import { apiClient } from "./client";

export interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  link_url: string | null;
  extra: Record<string, unknown>;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCount {
  count: number;
}

export interface NotificationPreference {
  type: string;
  in_app: boolean;
  email: boolean;
  push: boolean;
}

export interface NotificationPreferenceUpdate {
  in_app?: boolean;
  email?: boolean;
  push?: boolean;
}

export const notificationsService = {
  list: (params?: { limit?: number; offset?: number; unread_only?: boolean }) =>
    apiClient
      .get<Notification[]>("/notifications", { params })
      .then((r) => r.data),

  unreadCount: () =>
    apiClient.get<UnreadCount>("/notifications/unread-count").then((r) => r.data),

  markRead: (id: string) =>
    apiClient.post(`/notifications/${id}/read`).then(() => undefined),

  markAllRead: () =>
    apiClient.post<{ marked: number }>("/notifications/read-all").then((r) => r.data),

  preferences: () =>
    apiClient
      .get<NotificationPreference[]>("/notifications/preferences")
      .then((r) => r.data),

  updatePreference: (type: string, payload: NotificationPreferenceUpdate) =>
    apiClient
      .put<NotificationPreference>(`/notifications/preferences/${type}`, payload)
      .then((r) => r.data),
};
