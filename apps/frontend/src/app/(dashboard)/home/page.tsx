"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAgents } from "@/features/agents/hooks/useAgents";

/**
 * Auth landing route. Routes signed-in users to:
 *   - `/welcome`   — first-time user with no agents yet (onboarding wizard)
 *   - `/libraries` — returning user with one or more agents
 *
 * Wait for the agents query before deciding so we don't flicker between
 * the two destinations.
 */
export default function HomePage() {
  const router = useRouter();
  const { data: agents, isLoading } = useAgents();

  useEffect(() => {
    if (isLoading) return;
    if (!agents || agents.length === 0) {
      router.replace("/welcome");
    } else {
      router.replace("/libraries");
    }
  }, [router, agents, isLoading]);

  return (
    <div className="flex h-screen items-center justify-center">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}
