"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/features/auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { useDocumentProgress } from "@/features/knowledge/hooks/useDocumentProgress";
import { cn } from "@/lib/utils";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isAgentChatRoute = /^\/agents\/[^/]+\/chat$/.test(pathname);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Bridge ingestion socket events → TanStack cache (realtime progress UI)
  useDocumentProgress();

  // Guard 1: must be authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Guard 2: must be verified — hard block, send to /verify-email/pending
  useEffect(() => {
    if (isLoading || !user) return;
    if (!user.is_verified) {
      router.replace("/verify-email/pending");
    }
  }, [isLoading, user, router]);

  if (isLoading || !isAuthenticated || (user && !user.is_verified)) {
    return (
      <div className="flex h-[100dvh] items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted border-t-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background text-foreground">
      <Sidebar collapsed={!sidebarOpen} />
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <Header sidebarOpen={sidebarOpen} onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <main
          className={cn(
            "min-h-0 flex-1",
            isAgentChatRoute ? "overflow-hidden" : "scrollbar-thin overflow-auto"
          )}
        >
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
