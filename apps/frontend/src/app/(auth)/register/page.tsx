import { Metadata } from "next";
import { RegisterView } from "@/features/auth";

export const metadata: Metadata = {
  title: "Create Account | AI Agent Builder",
};

export default function RegisterPage() {
  return <RegisterView />;
}
