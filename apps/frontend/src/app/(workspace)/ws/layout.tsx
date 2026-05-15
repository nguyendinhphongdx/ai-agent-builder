"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/features/auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { useDocumentProgress } from "@/features/knowledge/hooks/useDocumentProgress";
import { useSession } from "@/features/workspaces";
import { cn } from "@/lib/utils";

/**
 * Workspace-scoped dashboard shell.
 *
 * URL: ``/ws/...`` — the workspace identity lives in the
 * ``access_token`` cookie's ``ws`` claim (set by
 * /api/auth/enter-workspace). The URL prefix is purely
 * presentational + reminds the user they're in a workspace context.
 *
 * Layout responsibilities:
 *   1. Require authentication + email verification.
 *   2. Require ``scope=workspace`` token. ``scope=user`` → redirect
 *      to /org (the user hasn't picked a workspace yet).
 */
export default function WorkspaceDashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const sessionQ = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const isAgentChatRoute = /\/agents\/[^/]+\/chat$/.test(pathname);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useDocumentProgress();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login");
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user) return;
    if (!user.is_verified) router.replace("/verify-email/pending");
  }, [isLoading, user, router]);

  useEffect(() => {
    if (sessionQ.isLoading || !sessionQ.data) return;
    if (sessionQ.data.token_scope !== "workspace") {
      router.replace("/org/workspaces");
    }
  }, [sessionQ.isLoading, sessionQ.data, router]);

  const ready =
    !isLoading &&
    isAuthenticated &&
    user?.is_verified &&
    sessionQ.data?.token_scope === "workspace";

  if (!ready) {
    return (
      <div className="flex h-[100dvh] items-center justify-center bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background text-foreground">
      <Sidebar collapsed={!sidebarOpen} />
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <Header
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />
        <main
          className={cn(
            "min-h-0 flex-1",
            isAgentChatRoute ? "overflow-hidden" : "scrollbar-thin overflow-auto",
          )}
        >
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
