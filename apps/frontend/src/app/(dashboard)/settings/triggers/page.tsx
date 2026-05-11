import type { Metadata } from "next";
import { TriggersView } from "@/features/triggers/views/TriggersView";

export const metadata: Metadata = {
  title: "Triggers · Settings | AgentForge",
};

export default function TriggersPage() {
  return <TriggersView />;
}
