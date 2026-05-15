import type { Metadata } from "next";
import { AnnotationsView } from "@/features/annotations/views/AnnotationsView";

export const metadata: Metadata = {
  title: "Quality & Feedback · Settings | AgentForge",
};

export default function AnnotationsPage() {
  return <AnnotationsView />;
}
