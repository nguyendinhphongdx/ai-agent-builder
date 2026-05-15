"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * /org root → bounce to /org/workspaces (the canonical first tab).
 * Phase 4 may replace this with an overview/dashboard.
 */
export default function OrgIndexPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/org/workspaces");
  }, [router]);
  return null;
}
