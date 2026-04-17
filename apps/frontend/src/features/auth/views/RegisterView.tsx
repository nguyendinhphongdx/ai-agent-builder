"use client";

import { AuthLayout } from "../components/AuthLayout";
import { RegisterForm } from "../components/RegisterForm";

export function RegisterView() {
  return (
    <AuthLayout
      title="Create your account"
      subtitle="Get started building AI agents in minutes"
    >
      <RegisterForm />
    </AuthLayout>
  );
}
