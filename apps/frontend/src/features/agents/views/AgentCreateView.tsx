"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AgentForm } from "../components/AgentForm";
import { useCreateAgent } from "../hooks/useAgents";

export function AgentCreateView() {
  const createAgent = useCreateAgent();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/agents" className={buttonVariants({ variant: "ghost", size: "icon" })}>
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h1 className="text-2xl font-bold">Create Agent</h1>
      </div>

      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Agent Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <AgentForm
            onSubmit={(data) => createAgent.mutate(data)}
            isPending={createAgent.isPending}
          />
        </CardContent>
      </Card>
    </div>
  );
}
