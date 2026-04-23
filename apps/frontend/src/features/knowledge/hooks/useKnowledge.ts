"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { knowledgeService } from "../services/knowledgeService";
import type { KBCreateInput, KBUpdateInput } from "../types";

export const kbKeys = {
  all: ["knowledge-bases"] as const,
  list: () => [...kbKeys.all, "list"] as const,
  detail: (id: string) => [...kbKeys.all, "detail", id] as const,
  byAgent: (agentId: string) => [...kbKeys.all, "agent", agentId] as const,
  documents: (kbId: string) => [...kbKeys.all, "documents", kbId] as const,
  document: (kbId: string, docId: string) =>
    [...kbKeys.all, "document", kbId, docId] as const,
  chunks: (kbId: string, docId: string, limit: number, offset: number) =>
    [...kbKeys.all, "chunks", kbId, docId, limit, offset] as const,
};

/* ─── Queries ─────────────────────────────────────────────────────── */

export function useKnowledgeBases() {
  return useQuery({
    queryKey: kbKeys.list(),
    queryFn: knowledgeService.list,
  });
}

export function useKnowledgeBase(id: string) {
  return useQuery({
    queryKey: kbKeys.detail(id),
    queryFn: () => knowledgeService.getById(id),
    enabled: !!id,
  });
}

export function useKnowledgeBasesByAgent(agentId: string) {
  return useQuery({
    queryKey: kbKeys.byAgent(agentId),
    queryFn: () => knowledgeService.getByAgentId(agentId),
    enabled: !!agentId,
  });
}

export function useKBDocuments(kbId: string) {
  return useQuery({
    queryKey: kbKeys.documents(kbId),
    queryFn: () => knowledgeService.listDocuments(kbId),
    enabled: !!kbId,
  });
}

export function useKBDocument(kbId: string, docId: string) {
  return useQuery({
    queryKey: kbKeys.document(kbId, docId),
    queryFn: () => knowledgeService.getDocument(kbId, docId),
    enabled: !!kbId && !!docId,
  });
}

export function useKBChunks(kbId: string, docId: string, limit = 50, offset = 0) {
  return useQuery({
    queryKey: kbKeys.chunks(kbId, docId, limit, offset),
    queryFn: () => knowledgeService.listChunks(kbId, docId, limit, offset),
    enabled: !!kbId && !!docId,
  });
}

/* ─── Mutations ──────────────────────────────────────────────────── */

export function useCreateKnowledgeBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: KBCreateInput) => knowledgeService.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: kbKeys.list() }),
  });
}

export function useUpdateKnowledgeBase(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: KBUpdateInput) => knowledgeService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kbKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: kbKeys.list() });
    },
  });
}

export function useDeleteKnowledgeBase() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => knowledgeService.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: kbKeys.list() }),
  });
}

export function useUploadDocument(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => knowledgeService.uploadDocument(kbId, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kbKeys.documents(kbId) });
      queryClient.invalidateQueries({ queryKey: kbKeys.detail(kbId) });
    },
  });
}

export function useDeleteDocument(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => knowledgeService.deleteDocument(kbId, docId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: kbKeys.documents(kbId) });
      queryClient.invalidateQueries({ queryKey: kbKeys.detail(kbId) });
    },
  });
}

export function useReprocessDocument(kbId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (docId: string) => knowledgeService.reprocessDocument(kbId, docId),
    onSuccess: (doc) => {
      // Optimistic cache patch so the row instantly shows "queued" while the
      // server picks it up. Socket events will fill in subsequent phases.
      queryClient.setQueryData<typeof doc[] | undefined>(
        kbKeys.documents(kbId),
        (old) => old?.map((d) => (d.id === doc.id ? doc : d)),
      );
      queryClient.invalidateQueries({ queryKey: kbKeys.detail(kbId) });
    },
  });
}

export function useQueryKnowledgeBase(kbId: string) {
  return useMutation({
    mutationFn: ({ query, topK }: { query: string; topK?: number }) =>
      knowledgeService.query(kbId, query, topK),
  });
}

export function useAttachKBToAgent(agentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (kbId: string) => knowledgeService.attachToAgent(agentId, kbId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: kbKeys.byAgent(agentId) }),
  });
}

export function useDetachKBFromAgent(agentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (kbId: string) => knowledgeService.detachFromAgent(agentId, kbId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: kbKeys.byAgent(agentId) }),
  });
}
