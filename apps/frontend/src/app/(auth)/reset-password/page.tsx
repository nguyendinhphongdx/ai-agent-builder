import { Metadata } from "next";
import { Suspense } from "react";
import { ResetPasswordView } from "@/features/auth";

export const metadata: Metadata = {
  title: "Reset password | AI Agent Builder",
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordView />
    </Suspense>
  );
}
