"use client";

import { memo } from "react";
import Link from "next/link";
import { Bot, MessageSquare } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import type { AgentListItem } from "../types";

interface AgentCardProps {
  agent: AgentListItem;
}

export const AgentCard = memo(function AgentCard({ agent }: AgentCardProps) {
  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Bot className="h-4 w-4 text-primary" />
          </div>
          <div>
            <CardTitle className="text-base">
              <Link href={`/agents/${agent.id}`} className="hover:underline">
                {agent.name}
              </Link>
            </CardTitle>
          </div>
        </div>
        <Badge variant={agent.status === "active" ? "default" : "secondary"}>
          {agent.status}
        </Badge>
      </CardHeader>
      <CardContent>
        <p className="mb-3 line-clamp-2 text-sm text-muted-foreground">
          {agent.description || "No description"}
        </p>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            {agent.llm_model}
          </span>
          <Link href={`/agents/${agent.id}/chat`} className={buttonVariants({ variant: "outline", size: "sm" })}>
            <MessageSquare className="mr-1 h-3 w-3" />
            Chat
          </Link>
        </div>
      </CardContent>
    </Card>
  );
});
