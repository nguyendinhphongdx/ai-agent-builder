import axios, { AxiosError, AxiosRequestConfig } from "axios";

// ─────────────────────────────────────────────────────────────────────────────
// Client
// ─────────────────────────────────────────────────────────────────────────────

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// ─────────────────────────────────────────────────────────────────────────────
// Session state
//
//  refreshInFlight  – deduplicates concurrent 401s into a single refresh call
//  refreshFailed    – once the refresh endpoint itself fails, fail every
//                     subsequent request immediately without hitting the server
// ─────────────────────────────────────────────────────────────────────────────

let refreshInFlight: Promise<void> | null = null;
let refreshFailed   = false;

export function resetSession(): void {
  refreshInFlight = null;
  refreshFailed   = false;
}

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function performRefresh(): Promise<void> {
  refreshInFlight ??= axios
    .post(`${apiClient.defaults.baseURL}/auth/refresh`, {}, { withCredentials: true })
    .then(() => undefined)
    .finally(() => { refreshInFlight = null; });

  return refreshInFlight;
}

// Public auth-flow pages where 401 is the *expected* state (the user is
// supposed to be signed out). Bouncing them to /login from these breaks
// the flow — most visibly, clicking a password-reset link with no
// active session bounced to /login before the page could render.
const PUBLIC_AUTH_PATHS = [
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
];

function redirectToLogin(): void {
  if (typeof window === "undefined") return;
  if (PUBLIC_AUTH_PATHS.some((p) => window.location.pathname.startsWith(p))) {
    return;
  }
  window.location.href = "/login";
}

// ─────────────────────────────────────────────────────────────────────────────
// Interceptor
// ─────────────────────────────────────────────────────────────────────────────

type RetryableConfig = AxiosRequestConfig & { _retry?: boolean };

apiClient.interceptors.response.use(
  (response) => response,

  async (error: AxiosError) => {
    const config = error.config as RetryableConfig | undefined;

    if (refreshFailed || error.response?.status !== 401 || !config || config._retry) {
      return Promise.reject(error);
    }

    config._retry = true;

    try {
      await performRefresh();
      return apiClient(config);
    } catch {
      refreshFailed = true;
      redirectToLogin();
      return Promise.reject(error);
    }
  },
);