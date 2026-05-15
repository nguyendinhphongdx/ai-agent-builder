import { Metadata } from "next";
import { ToolListView } from "@/features/tools";

export const metadata: Metadata = {
  title: "Tools | AgentForge",
};

export default function ToolsPage() {
  return <ToolListView />;
}
