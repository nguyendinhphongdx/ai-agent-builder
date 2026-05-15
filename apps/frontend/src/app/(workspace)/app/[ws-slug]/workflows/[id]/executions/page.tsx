"use client";

import { use } from "react";
import { WorkflowExecutionsView } from "@/features/workflows";

export default function WorkflowExecutionsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <WorkflowExecutionsView workflowId={id} />;
}
