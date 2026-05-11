import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Holds the **current** workspace id for the app. Persisted to
 * localStorage so a tab refresh keeps the user in the same workspace
 * they were last in.
 *
 * Note: this is the *intent* — what the user picked. The actual
 * permission/membership check happens server-side on every request
 * (auth dep reads ``X-Workspace-Id`` header → falls back to
 * ``user.default_workspace_id``). If the persisted id no longer maps
 * to a workspace the user can access, the BE returns 404 and the FE
 * should reset to the user's default.
 */
interface WorkspaceState {
  currentWorkspaceId: string | null;
  setCurrentWorkspaceId: (id: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      currentWorkspaceId: null,
      setCurrentWorkspaceId: (id) => set({ currentWorkspaceId: id }),
    }),
    {
      name: "agentforge:current-workspace",
    },
  ),
);
