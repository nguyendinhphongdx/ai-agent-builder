import { apiClient } from "@/lib/api/client";
import type {
  BrowseFilters,
  BrowseResponse,
  ForkResponse,
  PublishInput,
  Review,
  ReviewInput,
  TemplateDetail,
  TemplateSummary,
  UpdateTemplateInput,
} from "../types";

export const templateService = {
  browse: (filters: BrowseFilters = {}) =>
    apiClient
      .get<BrowseResponse>("/templates", { params: filters })
      .then((r) => r.data),

  detail: (slugOrId: string) =>
    apiClient.get<TemplateDetail>(`/templates/${slugOrId}`).then((r) => r.data),

  fork: (templateId: string) =>
    apiClient
      .post<ForkResponse>(`/templates/${templateId}/fork`)
      .then((r) => r.data),

  publish: (agentId: string, body: PublishInput) =>
    apiClient
      .post<TemplateSummary>(`/templates/publish-agent/${agentId}`, body)
      .then((r) => r.data),

  update: (templateId: string, body: UpdateTemplateInput) =>
    apiClient
      .patch<TemplateSummary>(`/templates/${templateId}`, body)
      .then((r) => r.data),

  archive: (templateId: string) =>
    apiClient.delete(`/templates/${templateId}`),

  myPublished: () =>
    apiClient
      .get<TemplateSummary[]>("/templates/me/published")
      .then((r) => r.data),

  myForkAgentIds: () =>
    apiClient.get<string[]>("/templates/me/forks").then((r) => r.data),

  listReviews: (templateId: string) =>
    apiClient
      .get<Review[]>(`/templates/${templateId}/reviews`)
      .then((r) => r.data),

  upsertReview: (templateId: string, body: ReviewInput) =>
    apiClient
      .put<Review>(`/templates/${templateId}/reviews/me`, body)
      .then((r) => r.data),

  deleteReview: (templateId: string) =>
    apiClient.delete(`/templates/${templateId}/reviews/me`),

  // Stripe paid flow (V2)
  purchase: (templateId: string) =>
    apiClient
      .post<{ checkout_url: string; purchase_id: string }>(
        `/templates/${templateId}/purchase`,
      )
      .then((r) => r.data),

  purchaseStatus: (sessionId: string) =>
    apiClient
      .get<{ status: string; template_id: string; agent_id: string | null }>(
        `/templates/purchases/${sessionId}/status`,
      )
      .then((r) => r.data),
};
