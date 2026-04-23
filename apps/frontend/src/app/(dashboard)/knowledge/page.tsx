import { Metadata } from "next";
import { KnowledgeListView } from "@/features/knowledge/views/KnowledgeListView";

export const metadata: Metadata = {
  title: "Knowledge | AgentForge",
};

export default function KnowledgePage() {
  return <KnowledgeListView />;
}
