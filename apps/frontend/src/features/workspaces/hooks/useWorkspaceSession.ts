"use client";

import { useQuery } from "@tanstack/react-query";
import { sessionService } from "@/lib/api/sessionService";

/**
 * Read the active session's scope + claims. Phase 2 of the Hub
 * refactor (docs/architecture/hub-auth-refactor.md) makes this the
 * canonical source of "which workspace am I in" — replaces the
 * localStorage-backed zustand store.
 *
 * Cached for 5 min: a workspace switch goes through ``enter-workspace``
 * which invalidates every query via ``qc.invalidateQueries()``, so
 * the next read of this hook refetches.
 */
export const sessionKeys = {
  current: ["auth", "session"] as const,
};

export function useSession() {
  return useQuery({
    queryKey: sessionKeys.current,
    queryFn: () => sessionService.get(),
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
