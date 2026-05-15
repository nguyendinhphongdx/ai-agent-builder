"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/features/auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { useDocumentProgress } from "@/features/knowledge/hooks/useDocumentProgress";
import { useSession } from "@/features/workspaces";
import { cn } from "@/lib/utils";

// Pages that legitimately live OUTSIDE a workspace context — they
// belong under the (dashboard) layout but don't require a
// ``scope=workspace`` token. Visiting any of these with a user_token
// is fine; visiting anything that loads workspace-scoped data (the
// rest of /settings, e.g. credentials/usage/api-tokens) routes to
// /org first so the user picks a workspace.
const NON_WORKSPACE_PREFIXES = [
  "/admin",
  "/hub",
  "/notifications",
  "/workspaces/invitations",
  "/settings/profile",
  "/settings/security",
  "/settings/preferences",
  "/settings/payouts",
  "/settings/billing",
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const sessionQ = useSession();
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

  // Guard 3 (Phase 2): visitors holding a user_token on a workspace-
  // scoped legacy route get bounced to /org so they pick a workspace
  // first. Routes in NON_WORKSPACE_PREFIXES are exempt — they're
  // user-/org-scoped pages that work without a workspace claim.
  useEffect(() => {
    if (sessionQ.isLoading || !sessionQ.data) return;
    if (sessionQ.data.token_scope === "user") {
      const exempt = NON_WORKSPACE_PREFIXES.some((p) => pathname.startsWith(p));
      if (!exempt) router.replace("/org/workspaces");
    }
  }, [sessionQ.isLoading, sessionQ.data, pathname, router]);

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
