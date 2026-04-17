"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { LoadingState } from "@/components/shared/LoadingState";
import { EmptyState } from "@/components/shared/EmptyState";
import { AgentCard } from "../components/AgentCard";
import { useAgents } from "../hooks/useAgents";

export function AgentListView() {
  const { data: agents, isLoading } = useAgents();

  if (isLoading) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Agents</h1>
        <Link href="/agents/new" className={buttonVariants()}>
          <Plus className="mr-2 h-4 w-4" />
          New Agent
        </Link>
      </div>

      {!agents?.length ? (
        <EmptyState
          title="No agents yet"
          description="Create your first AI agent to get started"
          action={
            <Link href="/agents/new" className={buttonVariants()}>
              <Plus className="mr-2 h-4 w-4" />
              Create Agent
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  );
}
