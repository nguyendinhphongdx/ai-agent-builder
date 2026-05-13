/**
 * Best-effort extraction of an error message from axios-shaped errors.
 * Backend usually returns `{ detail: string }` or `{ detail: object }`.
 */
export function extractError(err: unknown): string {
  const anyErr = err as {
    response?: { data?: { detail?: string | object } };
    message?: string;
  };
  const detail = anyErr?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return anyErr?.message ?? "Request failed";
}
