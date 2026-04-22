import { Metadata } from "next";
import { ForgotPasswordView } from "@/features/auth";

export const metadata: Metadata = {
  title: "Forgot Password | AI Agent Builder",
};

export default function ForgotPasswordPage() {
  return <ForgotPasswordView />;
}
