"use client";

import { use } from "react";
import { DocumentChunksView } from "@/features/knowledge/views/DocumentChunksView";

export default function DocumentChunksPage({
  params,
}: {
  params: Promise<{ id: string; docId: string }>;
}) {
  const { id, docId } = use(params);
  return <DocumentChunksView kbId={id} docId={docId} />;
}
