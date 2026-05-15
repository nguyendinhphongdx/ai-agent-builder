/**
 * Public surface of the workspaces feature.
 *
 * Cross-feature imports should go through this barrel — the
 * project's ESLint rule discourages reaching into another feature's
 * internal files (``features/workspaces/hooks/...``). Anything not
 * re-exported here is private to the feature.
 */

export { useWorkspacePath } from "./hooks/useWorkspacePath";
export { useSession, sessionKeys } from "./hooks/useWorkspaceSession";
export {
  useWorkspaces,
  useWorkspace,
  useCreateWorkspace,
  useUpdateWorkspace,
  useDeleteWorkspace,
  useWorkspaceMembers,
  useUpdateMemberRole,
  useRemoveMember,
  useWorkspaceInvitations,
  useCreateInvitation,
  useRevokeInvitation,
  workspaceKeys,
} from "./hooks/useWorkspaces";
export { WorkspaceSwitcher } from "./components/WorkspaceSwitcher";
export { roleAtLeast, type WorkspaceRole } from "./types";
