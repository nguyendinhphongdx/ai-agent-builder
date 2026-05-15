"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * /hub root → bounce to /hub/workspaces (the canonical first tab).
 * Phase 4 may replace this with an overview/dashboard.
 */
export default function HubIndexPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/hub/workspaces");
  }, [router]);
  return null;
}
