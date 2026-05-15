"use client";

import { use } from "react";
import { WorkflowEditorView } from "@/features/workflows";

export default function WorkflowEditorPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <WorkflowEditorView workflowId={id} />;
}
