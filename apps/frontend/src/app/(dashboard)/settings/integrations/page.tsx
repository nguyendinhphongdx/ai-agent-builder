import type { Metadata } from "next";
import { IntegrationsHubView } from "@/features/integrations/views/IntegrationsHubView";

export const metadata: Metadata = {
  title: "Integrations | AgentForge",
};

export default function IntegrationsHubPage() {
  return <IntegrationsHubView />;
}
