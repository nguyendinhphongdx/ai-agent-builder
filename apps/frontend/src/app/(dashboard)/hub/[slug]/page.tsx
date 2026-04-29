"use client";

import { use } from "react";
import { HubDetailView } from "@/features/hub/views/HubDetailView";

export default function HubDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  return <HubDetailView slugOrId={slug} />;
}
