import { Metadata } from "next";
import { AgentEditorView } from "@/features/agents/views/AgentEditorView";

export const metadata: Metadata = {
  title: "New Agent | AgentForge",
};

export default function NewAgentPage() {
  return <AgentEditorView />;
}
