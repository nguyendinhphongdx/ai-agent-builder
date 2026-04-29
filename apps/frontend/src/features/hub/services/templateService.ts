import { apiClient } from "@/lib/api/client";
import type {
  BrowseFilters,
  BrowseResponse,
  ForkResponse,
  PublishInput,
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
};
