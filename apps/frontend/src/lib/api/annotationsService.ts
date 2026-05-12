import { apiClient } from "./client";

export interface Annotation {
  id: string;
  message_id: string;
  rating: number;
  feedback: string | null;
  expected_response: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface AnnotationTotals {
  up: number;
  down: number;
  total: number;
  up_rate: number;
  since: string;
}

export interface AnnotationTagRow {
  tag: string;
  count: number;
}

export interface AnnotationUpsertPayload {
  rating: -1 | 1;
  feedback?: string | null;
  expected_response?: string | null;
  tags?: string[] | null;
}

export const annotationsService = {
  get: (messageId: string) =>
    apiClient
      .get<Annotation | null>(`/messages/${messageId}/annotation`)
      .then((r) => r.data),
  upsert: (messageId: string, payload: AnnotationUpsertPayload) =>
    apiClient
      .put<Annotation>(`/messages/${messageId}/annotation`, payload)
      .then((r) => r.data),
  remove: (messageId: string) =>
    apiClient.delete(`/messages/${messageId}/annotation`).then(() => undefined),
  totals: () =>
    apiClient.get<AnnotationTotals>("/annotations/totals").then((r) => r.data),
  topTags: (limit = 10) =>
    apiClient
      .get<AnnotationTagRow[]>("/annotations/tags", { params: { limit } })
      .then((r) => r.data),
  recentNegative: (limit = 50) =>
    apiClient
      .get<Annotation[]>("/annotations/recent-negative", { params: { limit } })
      .then((r) => r.data),
};
