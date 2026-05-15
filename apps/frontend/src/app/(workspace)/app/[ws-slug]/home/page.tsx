"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAgents } from "@/features/agents/hooks/useAgents";
import { HomeView } from "@/features/dashboard/views/HomeView";

/**
 * Workspace-scoped home (Phase 2 of Hub refactor). Mirrors the legacy
 * /home page but lives under /app/{ws-slug}/home — the URL slug
 * matches the workspace_token's ``ws`` claim.
 */
export default function WorkspaceHomePage() {
  const router = useRouter();
  const params = useParams();
  const wsSlug = (params?.["ws-slug"] as string) ?? "";
  const { data: agents, isLoading } = useAgents();

  useEffect(() => {
    if (isLoading) return;
    if (!agents || agents.length === 0) {
      router.replace(`/app/${wsSlug}/welcome`);
    }
  }, [router, agents, isLoading, wsSlug]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    return null;
  }

  return <HomeView />;
}
