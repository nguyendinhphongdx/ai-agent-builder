"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";
import {
  jobService,
  TERMINAL_STATUSES,
  type JobRow,
  type JobStatus,
} from "@/lib/api/jobService";

export const jobKeys = {
  all: ["jobs"] as const,
  list: (filter: { job_type?: string; status?: JobStatus }) =>
    [...jobKeys.all, "list", filter] as const,
  detail: (id: string) => [...jobKeys.all, "detail", id] as const,
};

/**
 * Poll a single job until it reaches a terminal state.
 *
 * Polling cadence:
 *   - active (queued/running/failed): 2s
 *   - terminal (completed/dead): stop polling entirely
 *
 * Returns standard TanStack Query state — caller can inspect
 * `data.status` to drive UI.
 */
export function useJob(
  id: string | null | undefined,
  options?: { pollMs?: number },
): UseQueryResult<JobRow> {
  const pollMs = options?.pollMs ?? 2000;
  return useQuery({
    queryKey: jobKeys.detail(id ?? ""),
    queryFn: () => jobService.get(id!),
    enabled: !!id,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (status && TERMINAL_STATUSES.has(status)) return false;
      return pollMs;
    },
    // No need to keep stale polling alive on tab blur.
    refetchOnWindowFocus: false,
  });
}

/** List the caller's jobs in the current workspace. Optional
 *  job_type / status filters. Polls every 5s by default for the
 *  in-flight set — drop pollMs to 0 to disable. */
export function useJobs(
  filter: { job_type?: string; status?: JobStatus } = {},
  options?: { pollMs?: number },
): UseQueryResult<JobRow[]> {
  const pollMs = options?.pollMs ?? 5000;
  return useQuery({
    queryKey: jobKeys.list(filter),
    queryFn: () => jobService.list(filter),
    refetchInterval: pollMs > 0 ? pollMs : false,
    refetchOnWindowFocus: false,
  });
}
