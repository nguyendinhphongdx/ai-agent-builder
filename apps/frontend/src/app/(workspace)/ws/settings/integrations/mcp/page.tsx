import type { Metadata } from "next";
import { McpView } from "@/features/integrations/views/McpView";

export const metadata: Metadata = {
  title: "MCP Server · Integrations | AgentForge",
};

export default function McpIntegrationPage() {
  return <McpView />;
}
