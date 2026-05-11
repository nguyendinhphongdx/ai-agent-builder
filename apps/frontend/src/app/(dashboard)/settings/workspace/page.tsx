import type { Metadata } from "next";
import { WorkspaceSettingsView } from "@/features/workspaces/views/WorkspaceSettingsView";

export const metadata: Metadata = {
  title: "Workspace · Settings | AgentForge",
};

export default function WorkspaceSettingsPage() {
  return <WorkspaceSettingsView />;
}
