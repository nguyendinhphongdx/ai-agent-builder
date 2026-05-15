import { Metadata } from "next";
import { KnowledgeCreateWizard } from "@/features/knowledge/views/KnowledgeCreateWizard";

export const metadata: Metadata = {
  title: "Create Knowledge | AgentForge",
};

export default function KnowledgeCreatePage() {
  return <KnowledgeCreateWizard />;
}
