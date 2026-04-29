"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { templateService } from "../services/templateService";
import type {
  BrowseFilters,
  PublishInput,
  ReviewInput,
  UpdateTemplateInput,
} from "../types";

export const templateKeys = {
  all: ["templates"] as const,
  browse: (filters: BrowseFilters) => [...templateKeys.all, "browse", filters] as const,
  detail: (id: string) => [...templateKeys.all, "detail", id] as const,
  myPublished: () => [...templateKeys.all, "mine", "published"] as const,
  myForks: () => [...templateKeys.all, "mine", "forks"] as const,
  reviews: (templateId: string) => [...templateKeys.all, "reviews", templateId] as const,
};

export function useBrowseTemplates(filters: BrowseFilters = {}) {
  return useQuery({
    queryKey: templateKeys.browse(filters),
    queryFn: () => templateService.browse(filters),
    staleTime: 30_000,
  });
}

export function useTemplate(slugOrId: string) {
  return useQuery({
    queryKey: templateKeys.detail(slugOrId),
    queryFn: () => templateService.detail(slugOrId),
    enabled: !!slugOrId,
  });
}

export function useForkTemplate() {
  const queryClient = useQueryClient();
  const router = useRouter();

  return useMutation({
    mutationFn: (templateId: string) => templateService.fork(templateId),
    onSuccess: (data) => {
      // Invalidate user's agent list so the new fork appears, then jump there.
      queryClient.invalidateQueries({ queryKey: ["agents"] });
      queryClient.invalidateQueries({ queryKey: templateKeys.myForks() });
      router.push(`/agents/${data.agent_id}`);
    },
  });
}

export function usePublishAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ agentId, input }: { agentId: string; input: PublishInput }) =>
      templateService.publish(agentId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.myPublished() });
      queryClient.invalidateQueries({ queryKey: templateKeys.all });
    },
  });
}

export function useUpdateTemplate(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: UpdateTemplateInput) =>
      templateService.update(templateId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.detail(templateId) });
      queryClient.invalidateQueries({ queryKey: templateKeys.myPublished() });
    },
  });
}

export function useArchiveTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) => templateService.archive(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.all });
    },
  });
}

export function useMyPublishedTemplates() {
  return useQuery({
    queryKey: templateKeys.myPublished(),
    queryFn: templateService.myPublished,
  });
}

export function useTemplateReviews(templateId: string) {
  return useQuery({
    queryKey: templateKeys.reviews(templateId),
    queryFn: () => templateService.listReviews(templateId),
    enabled: !!templateId,
  });
}

export function useUpsertReview(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ReviewInput) =>
      templateService.upsertReview(templateId, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.reviews(templateId) });
      // rating_avg + rating_count on the template change too
      queryClient.invalidateQueries({ queryKey: templateKeys.detail(templateId) });
      queryClient.invalidateQueries({ queryKey: templateKeys.all });
    },
  });
}

export function useDeleteReview(templateId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => templateService.deleteReview(templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: templateKeys.reviews(templateId) });
      queryClient.invalidateQueries({ queryKey: templateKeys.detail(templateId) });
    },
  });
}
