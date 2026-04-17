import type { Metadata } from "next";
import { ToolCreateView } from "@/features/tools/views/ToolCreateView";

export const metadata: Metadata = {
  title: "Create Tool | AgentForge",
};

export default function NewToolPage() {
  return <ToolCreateView />;
}
