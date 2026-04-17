import { Metadata } from "next";
import { LoginView } from "@/features/auth";

export const metadata: Metadata = {
  title: "Sign In | AI Agent Builder",
};

export default function LoginPage() {
  return <LoginView />;
}
