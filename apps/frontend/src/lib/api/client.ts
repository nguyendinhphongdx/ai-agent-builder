import axios, { AxiosError, AxiosRequestConfig } from "axios";

// ─────────────────────────────────────────────────────────────────────────────
// Client
// ─────────────────────────────────────────────────────────────────────────────

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// Workspace context now lives in the access_token cookie (Phase 0+
// of the Hub refactor — see docs/architecture/hub-auth-refactor.md).
// No more X-Workspace-Id interceptor; the BE reads the ``ws`` claim
// from the JWT directly. The legacy header is still accepted on the
// BE as a back-compat fallback but no FE code path sends it.
//
// Org context, however, is *not* in the token — a user can belong
// to N orgs and pick which one's Hub they're viewing. The selection
// is persisted in localStorage (see ``useActiveOrgId``) and sent on
// every request so org-scoped routes resolve against the right org.
// The BE falls back to ``user.default_organization_id`` when the
// header is absent, so a missing/disabled localStorage still works
// — single-org users never need to set it.
const ACTIVE_ORG_STORAGE_KEY = "agentforge:current-org";

apiClient.interceptors.request.use((config) => {
  if (typeof window === "undefined") return config;
  let orgId: string | null = null;
  try {
    orgId = window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY);
  } catch {
    orgId = null;
  }
  if (orgId) {
    config.headers = config.headers ?? {};
    config.headers["X-Organization-Id"] = orgId;
  }
  return config;
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