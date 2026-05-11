import type { Metadata } from "next";
import { UsageView } from "@/features/usage/views/UsageView";

export const metadata: Metadata = {
  title: "Usage & Cost · Settings | AgentForge",
};

export default function UsagePage() {
  return <UsageView />;
}
