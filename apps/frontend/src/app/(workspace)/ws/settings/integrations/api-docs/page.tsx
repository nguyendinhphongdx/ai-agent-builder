import type { Metadata } from "next";
import { ApiDocsView } from "@/features/integrations/views/ApiDocsView";

export const metadata: Metadata = {
  title: "REST API · Integrations | AgentForge",
};

export default function ApiDocsPage() {
  return <ApiDocsView />;
}
