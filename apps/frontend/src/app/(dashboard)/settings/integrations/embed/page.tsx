import type { Metadata } from "next";
import { EmbedView } from "@/features/integrations/views/EmbedView";

export const metadata: Metadata = {
  title: "Web Embed · Integrations | AgentForge",
};

export default function EmbedIntegrationPage() {
  return <EmbedView />;
}
