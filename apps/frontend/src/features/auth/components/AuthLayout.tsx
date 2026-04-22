"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Bot, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useAuth } from "../hooks/useAuth";
import { BrandPanel } from "./BrandPanel";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

const VERIFY_PENDING_PATH = "/verify-email/pending";

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="absolute top-4 right-4 z-20 flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background/60 text-muted-foreground backdrop-blur-sm transition-colors hover:bg-accent hover:text-foreground"
      aria-label="Toggle theme"
    >
      <Sun className="h-4 w-4 scale-100 rotate-0 transition-transform dark:scale-0 dark:-rotate-90" />
      <Moon className="absolute h-4 w-4 scale-0 rotate-90 transition-transform dark:scale-100 dark:rotate-0" />
    </button>
  );
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // Auth pages shouldn't be visible to already-signed-in users.
  // - Verified → send to /home (which forwards to the real app)
  // - Unverified → keep them on the verify-email page, redirect others
  useEffect(() => {
    if (isLoading || !isAuthenticated || !user) return;
    if (user.is_verified) {
      router.replace("/home");
    } else if (pathname !== VERIFY_PENDING_PATH) {
      router.replace(VERIFY_PENDING_PATH);
    }
  }, [isLoading, isAuthenticated, user, pathname, router]);

  return (
    <div className="relative flex min-h-screen">
      {/* Theme toggle — top right of the whole page */}
      <ThemeToggle />

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
