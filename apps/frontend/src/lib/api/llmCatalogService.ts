import { apiClient } from "./client";
import type { ModelCatalogEntry, ProviderEntry } from "@/lib/models/catalog";

export interface CatalogResponse {
  providers: ProviderEntry[];
  models: ModelCatalogEntry[];
}

export const llmCatalogService = {
  get: (): Promise<CatalogResponse> =>
    apiClient.get<CatalogResponse>("/llm/catalog").then((r) => r.data),
};
