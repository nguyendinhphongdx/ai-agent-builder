import { Metadata } from "next";
import { AgentLibraryView } from "@/features/agents/views/AgentLibraryView";

export const metadata: Metadata = {
  title: "Libraries | AgentForge",
  description: "Browse and manage your AI agents",
};

export default function LibrariesPage() {
  return <AgentLibraryView />;
}
