import type { Metadata } from "next";
import { AcceptInvitationView } from "@/features/workspaces/views/AcceptInvitationView";

export const metadata: Metadata = {
  title: "Accept invitation | AgentForge",
};

export default async function AcceptInvitationPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <AcceptInvitationView token={token} />;
}
