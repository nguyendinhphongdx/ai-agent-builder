"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAgents } from "@/features/agents/hooks/useAgents";
import { HomeView } from "@/features/dashboard/views/HomeView";

/**
 * Authenticated home — shows the dashboard for returning users with at least
 * one agent. Brand-new users (zero agents and no in-flight loading) bounce
 * to /welcome where the onboarding wizard surfaces starter templates.
 */
export default function HomePage() {
  const router = useRouter();
  const { data: agents, isLoading } = useAgents();

  useEffect(() => {
    if (isLoading) return;
    if (!agents || agents.length === 0) {
      router.replace("/welcome");
    }
  }, [router, agents, isLoading]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!agents || agents.length === 0) {
    // Redirect is in flight; render nothing instead of flickering the dashboard.
    return null;
  }

  return <HomeView />;
}
