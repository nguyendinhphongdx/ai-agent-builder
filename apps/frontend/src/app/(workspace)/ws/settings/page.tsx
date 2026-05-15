import type { Metadata } from "next";
import { WorkspaceSettingsView } from "@/features/workspaces/views/WorkspaceSettingsView";

export const metadata: Metadata = {
  title: "Workspace · Settings",
};

/** Workspace settings — General + Members + Danger zone (tabs
 *  inside the view). Sibling sub-routes under /ws/settings/* host
 *  resource-specific settings (credentials, integrations, etc.). */
export default function WorkspaceSettingsPage() {
  return <WorkspaceSettingsView />;
}
