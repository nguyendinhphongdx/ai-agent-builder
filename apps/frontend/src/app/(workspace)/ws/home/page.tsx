"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAgents } from "@/features/agents/hooks/useAgents";
import { HomeView } from "@/features/dashboard/views/HomeView";

/**
 * Workspace home (``/ws/home``). Empty-agent users bounce to the
 * welcome wizard at /ws/welcome.
 */
export default function WorkspaceHomePage() {
  const router = useRouter();
  const { data: agents, isLoading } = useAgents();

  useEffect(() => {
    if (isLoading) return;
    if (!agents || agents.length === 0) {
      router.replace("/ws/welcome");
    }
  }, [router, agents, isLoading]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!agents || agents.length === 0) return null;

  return <HomeView />;
}
