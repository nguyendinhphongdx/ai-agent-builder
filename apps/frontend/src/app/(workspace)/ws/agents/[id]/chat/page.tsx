"use client";

import { use } from "react";
import { ChatView } from "@/features/chat";

export default function AgentChatPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <ChatView agentId={id} />;
}
