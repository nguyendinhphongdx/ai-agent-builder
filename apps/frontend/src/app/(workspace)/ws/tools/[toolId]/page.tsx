import type { Metadata } from "next";
import { ToolDetailView } from "@/features/tools/views/ToolDetailView";

export const metadata: Metadata = {
  title: "Tool Detail | AgentForge",
};

export default async function ToolDetailPage({
  params,
}: {
  params: Promise<{ toolId: string }>;
}) {
  const { toolId } = await params;
  return <ToolDetailView toolId={toolId} />;
}
