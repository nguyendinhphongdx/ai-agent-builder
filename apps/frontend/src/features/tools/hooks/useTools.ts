"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toolService } from "../services/toolService";
import type { ToolCreateInput, ToolUpdateInput } from "../types";

export const toolKeys = {
  all: ["tools"] as const,
  list: () => [...toolKeys.all, "list"] as const,
  detail: (id: string) => [...toolKeys.all, "detail", id] as const,
};

export function useTools() {
  return useQuery({
    queryKey: toolKeys.list(),
    queryFn: toolService.list,
  });
}

export function useTool(id: string) {
  return useQuery({
    queryKey: toolKeys.detail(id),
    queryFn: () => toolService.getById(id),
    enabled: !!id,
  });
}

export function useCreateTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ToolCreateInput) => toolService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: toolKeys.list() });
    },
  });
}

export function useUpdateTool(id: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ToolUpdateInput) => toolService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: toolKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: toolKeys.list() });
    },
  });
}

export function useDeleteTool() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => toolService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: toolKeys.list() });
    },
  });
}

export function useTestTool() {
  return useMutation({
    mutationFn: ({ id, inputData }: { id: string; inputData: Record<string, unknown> }) =>
      toolService.test(id, inputData),
  });
}
