import { apiClient } from "./client";

/**
 * Two-stage auth session (see docs/architecture/hub-auth-refactor.md).
 *
 * After login the access_token cookie carries ``scope=user`` — the FE
 * should land on /hub. After ``enterWorkspace`` it carries
 * ``scope=workspace`` and the FE can render workspace-scoped pages.
 *
 * The cookie itself is HttpOnly so the FE can't read it directly;
 * ``/auth/session`` exposes the scope + claims through a normal JSON
 * response.
 */

export type TokenScope = "user" | "workspace";

export interface SessionState {
  token_scope: TokenScope;
  user_id: string;
  workspace_id: string | null;
  organization_id: string | null;
}

export interface EnterWorkspaceResponse {
  workspace_id: string;
  workspace_slug: string;
  workspace_name: string;
  organization_id: string;
  organization_slug: string;
}

export const sessionService = {
  /** Read the active token's scope + claims. Cheap — single decode + auth dep. */
  get: (): Promise<SessionState> =>
    apiClient.get<SessionState>("/auth/session").then((r) => r.data),

  /** Verify membership, mint a workspace-scoped token, replace the cookie.
   *  Caller follows up with ``router.push("/app/" + slug + "/home")``. */
  enter: (workspace_id: string): Promise<EnterWorkspaceResponse> =>
    apiClient
      .post<EnterWorkspaceResponse>("/auth/enter-workspace", { workspace_id })
      .then((r) => r.data),

  /** Replace the workspace cookie with a user-scoped one. Caller then
   *  routes to ``/hub``. */
  exit: (): Promise<void> =>
    apiClient.post("/auth/exit-workspace").then(() => undefined),
};
