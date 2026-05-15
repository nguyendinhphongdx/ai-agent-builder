"use client";

import { use } from "react";
import { AgentEditorView } from "@/features/agents/views/AgentEditorView";

export default function AgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <AgentEditorView agentId={id} />;
}
