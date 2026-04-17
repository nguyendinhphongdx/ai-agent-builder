"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";

export const kbKeys = {
  all: ["knowledge-bases"] as const,
  list: () => [...kbKeys.all, "list"] as const,
  detail: (id: string) => [...kbKeys.all, "detail", id] as const,
  byAgent: (agentId: string) => [...kbKeys.all, "agent", agentId] as const,
  documents: (kbId: string) => [...kbKeys.all, "documents", kbId] as const,
};

export function useKnowledgeBases() {
  return useQuery({
    queryKey: kbKeys.list(),
    queryFn: knowledgeService.list,
  });
}

export function useKnowledgeBasesByAgent(agentId: string) {
  return useQuery({
    queryKey: kbKeys.byAgent(agentId),
    queryFn: () => knowledgeService.getByAgentId(agentId),
    enabled: !!agentId,
  });
}

export function useKnowledgeBase(id: string) {
  return useQuery({
    queryKey: kbKeys.detail(id),
    queryFn: () => knowledgeService.getById(id),
    enabled: !!id,
  });
}

export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: knowledgeService.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: kbKeys.list() }),
  });
}

export function useKBDocuments(kbId: string) {
  return useQuery({
    queryKey: kbKeys.documents(kbId),
    queryFn: () => knowledgeService.listDocuments(kbId),
    enabled: !!kbId,
  });
}

export function useUploadDocument(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => knowledgeService.uploadDocument(kbId, file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: kbKeys.documents(kbId) }),
  });
}
