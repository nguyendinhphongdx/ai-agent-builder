"use client";

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { KnowledgeDetailView } from "@/features/knowledge/views/KnowledgeDetailView";

type TabId = "documents" | "retrieval" | "settings";

function isTab(v: string | null): v is TabId {
  return v === "documents" || v === "retrieval" || v === "settings";
}

export default function KnowledgeDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab");
  return <KnowledgeDetailView kbId={id} initialTab={isTab(tab) ? tab : "documents"} />;
}
