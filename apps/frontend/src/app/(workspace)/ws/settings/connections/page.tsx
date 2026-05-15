import type { Metadata } from "next";
import { ConnectionsView } from "@/features/connections";

export const metadata: Metadata = {
  title: "Connections | AgentForge",
};

export default function ConnectionsPage() {
  return <ConnectionsView />;
}
