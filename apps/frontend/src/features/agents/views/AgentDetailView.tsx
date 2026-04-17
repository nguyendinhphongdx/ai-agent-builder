"use client";

import { ArrowLeft, MessageSquare, Trash2 } from "lucide-react";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingState } from "@/components/shared/LoadingState";
import { AgentForm } from "../components/AgentForm";
import { useAgent, useUpdateAgent, useDeleteAgent } from "../hooks/useAgents";

interface AgentDetailViewProps {
  agentId: string;
}

export function AgentDetailView({ agentId }: AgentDetailViewProps) {
  const { data: agent, isLoading } = useAgent(agentId);
  const updateAgent = useUpdateAgent(agentId);
  const deleteAgent = useDeleteAgent();

  if (isLoading) return <LoadingState />;
  if (!agent) return <p>Agent not found</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/agents" className={buttonVariants({ variant: "ghost", size: "icon" })}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <h1 className="text-2xl font-bold">{agent.name}</h1>
          <Badge variant={agent.status === "active" ? "default" : "secondary"}>
            {agent.status}
          </Badge>
        </div>
        <div className="flex gap-2">
          <Link href={`/agents/${agentId}/chat`} className={buttonVariants({ variant: "outline" })}>
            <MessageSquare className="mr-2 h-4 w-4" />
            Chat
          </Link>
          <Button
            variant="destructive"
            size="icon"
            onClick={() => deleteAgent.mutate(agentId)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Agent Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <AgentForm
            defaultValues={{
              name: agent.name,
              description: agent.description ?? "",
              system_prompt: agent.system_prompt,
              llm_provider: agent.llm_provider,
              llm_model: agent.llm_model,
              welcome_message: agent.welcome_message ?? "",
            }}
            onSubmit={(data) => updateAgent.mutate(data)}
            isPending={updateAgent.isPending}
            submitLabel="Save Changes"
          />
        </CardContent>
      </Card>
    </div>
  );
}
