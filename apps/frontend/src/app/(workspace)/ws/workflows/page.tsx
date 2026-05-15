import { Metadata } from "next";
import { WorkflowListView } from "@/features/workflows";

export const metadata: Metadata = {
  title: "Workflows | AgentForge",
};

export default function WorkflowsPage() {
  return <WorkflowListView />;
}
