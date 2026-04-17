"use client";

import { useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { useAgent } from "@/features/agents/hooks/useAgents";
import { ChatWindow } from "../components/ChatWindow";

interface ChatViewProps {
  agentId: string;
}

export function ChatView({ agentId }: ChatViewProps) {
  const { data: agent } = useAgent(agentId);
  const searchParams = useSearchParams();
  const conversationId = searchParams.get("conversationId");

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 items-center gap-3 border-b px-4 py-2">
        <Link
          href={`/agents/${agentId}`}
          className={buttonVariants({ variant: "ghost", size: "icon" })}
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h2 className="font-semibold">{agent?.name ?? "Chat"}</h2>
      </div>

      <ChatWindow
        agentId={agentId}
        conversationId={conversationId}
        agentName={agent?.name}
        welcomeMessage={agent?.welcome_message ?? undefined}
      />
    </div>
  );
}
