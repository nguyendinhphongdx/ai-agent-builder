/**
 * Types + client-side helpers cho AI model catalog.
 *
 * Catalog data (list of providers/models) là SOURCE OF TRUTH ở backend —
 * file `apps/backend/app/llm/catalog.py`. Frontend fetch qua
 * `GET /api/llm/catalog` bằng hook `useModelCatalog` (TanStack,
 * staleTime Infinity — catalog không đổi trong session).
 *
 * Các helper dưới đây là pure functions có thể gọi sync:
 *  - `providerOfModel`: parse "provider/model" → "provider". Không cần catalog.
 *  - `findModel`, `findProvider`, `modelDisplayName`: nhận catalog đã fetch
 *    làm argument thay vì đọc biến global, để component luôn dùng data mới nhất
 *    từ hook.
 */

import { useQuery } from "@tanstack/react-query";
import { llmCatalogService, type CatalogResponse } from "@/lib/api/llmCatalogService";

export type ModelCapability = "tools" | "vision" | "json_mode" | "thinking";

export interface ModelCatalogEntry {
  id: string;              // "openai/gpt-4o"
  provider: string;
  model: string;
  name: string;
  context_window: number;
  max_output: number;
  capabilities: ModelCapability[];
  description: string;
}

export interface ProviderEntry {
  id: string;
  label: string;
  description: string;
}

/* ─── Hook ────────────────────────────────────────────────────────── */

export function useModelCatalog() {
  return useQuery<CatalogResponse>({
    queryKey: ["llm", "catalog"],
    queryFn: llmCatalogService.get,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}

/* ─── Pure helpers ───────────────────────────────────────────────── */

export function providerOfModel(id: string): string {
  const slash = id.indexOf("/");
  return slash >= 0 ? id.slice(0, slash) : id;
}

export function findModel(
  catalog: ModelCatalogEntry[] | undefined,
  id: string,
): ModelCatalogEntry | undefined {
  return catalog?.find((m) => m.id === id);
}

export function findProvider(
  providers: ProviderEntry[] | undefined,
  id: string,
): ProviderEntry | undefined {
  return providers?.find((p) => p.id === id);
}

/** Fallback-safe display name: catalog entry → model name, else parse string. */
export function modelDisplayName(
  catalog: ModelCatalogEntry[] | undefined,
  id: string,
): string {
  const entry = findModel(catalog, id);
  if (entry) return entry.name;
  const slash = id.indexOf("/");
  return slash >= 0 ? id.slice(slash + 1) : id;
}
