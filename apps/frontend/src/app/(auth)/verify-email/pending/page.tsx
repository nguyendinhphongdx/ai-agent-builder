import { Metadata } from "next";
import { VerifyEmailPendingView } from "@/features/auth";

export const metadata: Metadata = {
  title: "Check your email | AI Agent Builder",
};

export default function VerifyEmailPendingPage() {
  return <VerifyEmailPendingView />;
}
