import type { Metadata } from "next";
import { BillingView } from "@/features/billing/views/BillingView";

export const metadata: Metadata = {
  title: "Billing · Organization",
};

/**
 * Org → Billing tab. Re-uses ``BillingView`` from the legacy
 * /settings/billing route — billing has always been org-scoped
 * server-side, the legacy page just lived under the user-settings
 * URL. Phase 5+ can sunset /settings/billing once nothing links
 * there.
 */
export default function OrgBillingPage() {
  return <BillingView />;
}
