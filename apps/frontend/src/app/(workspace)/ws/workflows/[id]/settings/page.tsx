"use client";

import { use } from "react";
import { WorkflowSettingsView } from "@/features/workflows";

export default function WorkflowSettingsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  return <WorkflowSettingsView workflowId={id} />;
}
