import type { Metadata } from "next";
import { BillingView } from "@/features/billing/views/BillingView";

export const metadata: Metadata = {
  title: "Billing & Plan · Settings | AgentForge",
};

export default function BillingPage() {
  return <BillingView />;
}
