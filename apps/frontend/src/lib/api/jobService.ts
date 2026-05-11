import { apiClient } from "./client";

export type JobStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "dead";

export interface JobRow {
  id: string;
  job_type: string;
  status: JobStatus;
  attempt: number;
  max_attempts: number;
  error: string | null;
  result: Record<string, unknown> | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface JobListParams {
  job_type?: string;
  status?: JobStatus;
  limit?: number;
  offset?: number;
}

export const TERMINAL_STATUSES: ReadonlySet<JobStatus> = new Set([
  "completed",
  "dead",
]);

export const jobService = {
  list: (params?: JobListParams): Promise<JobRow[]> =>
    apiClient
      .get<JobRow[]>("/jobs", { params })
      .then((r) => r.data),

  get: (id: string): Promise<JobRow> =>
    apiClient.get<JobRow>(`/jobs/${id}`).then((r) => r.data),
};
