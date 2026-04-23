"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useSocketEvent } from "@/features/notifications/hooks/useSocketEvent";
import { kbKeys } from "./useKnowledge";
import type { DocumentProgressEvent, KBDocument, KBDocumentDetail } from "../types";

/**
 * Subscribe to `document:progress` socket events from ingestion pipeline and
 * mutate TanStack Query cache so any component rendering that document gets
 * live updates without polling.
 *
 * Mount this once at a high level (e.g. dashboard layout or KB views).
 */
export function useDocumentProgress() {
  const queryClient = useQueryClient();

  useSocketEvent<DocumentProgressEvent>("document:progress", (p) => {
    // Patch list cache for the KB
    queryClient.setQueryData<KBDocument[] | undefined>(
      kbKeys.documents(p.kb_id),
      (old) => {
        if (!old) return old;
        return old.map((d) =>
          d.id === p.doc_id
            ? {
                ...d,
                status: p.status,
                processing_phase: p.phase,
                processing_progress: p.progress,
                chunk_count: p.chunk_count,
                error_message: p.error_message,
              }
            : d,
        );
      },
    );

    // Patch detail cache for the specific document
    queryClient.setQueryData<KBDocumentDetail | undefined>(
      kbKeys.document(p.kb_id, p.doc_id),
      (old) => {
        if (!old) return old;
        return {
          ...old,
          status: p.status,
          processing_phase: p.phase,
          processing_progress: p.progress,
          chunk_count: p.chunk_count,
          error_message: p.error_message,
        };
      },
    );

    // When a doc finishes, refresh the KB (detail + any agent's attached list)
    // so total_documents / total_chunks update wherever the KB is rendered.
    if (p.status === "ready" || p.status === "failed") {
      queryClient.invalidateQueries({ queryKey: kbKeys.detail(p.kb_id) });
      // byAgent is keyed by agentId which we don't have here — invalidate the
      // whole "agent" subkey. Cheap: a handful of KBs per agent at most.
      queryClient.invalidateQueries({ queryKey: [...kbKeys.all, "agent"] });
    }
  });
}
