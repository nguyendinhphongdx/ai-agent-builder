"use client";

import { Bot } from "lucide-react";
import { BrandPanel } from "./BrandPanel";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen">
      {/* Left: Branding — hidden on mobile */}
      <div className="hidden lg:block lg:w-1/2">
        <div className="sticky top-0 h-screen">
          <BrandPanel />
        </div>
      </div>

      {/* Right: Form */}
      <div className="flex-1 flex flex-col justify-center px-6 py-12 lg:px-16">
        <div className="mx-auto w-full max-w-[400px]">
          {/* Mobile-only logo */}
          <div className="lg:hidden flex items-center gap-2.5 mb-10 animate-fade-up">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Bot className="h-4.5 w-4.5" />
            </div>
            <span className="text-lg font-semibold tracking-tight">AgentForge</span>
          </div>

          {/* Heading */}
          <div className="mb-8 animate-fade-up delay-100">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {subtitle && (
              <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>

          {/* Form content */}
          <div className="animate-fade-up delay-200">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
