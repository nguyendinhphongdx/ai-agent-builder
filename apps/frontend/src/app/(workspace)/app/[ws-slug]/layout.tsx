"use client";

import { use, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/features/auth";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { useDocumentProgress } from "@/features/knowledge/hooks/useDocumentProgress";
import { useSession } from "@/features/workspaces/hooks/useWorkspaceSession";
import { useWorkspaces } from "@/features/workspaces/hooks/useWorkspaces";
import { cn } from "@/lib/utils";

/**
 * Workspace-scoped dashboard shell — Phase 2 of the Hub refactor.
 *
 * URL: ``/app/{ws-slug}/...`` — the slug is presentational; the
 * actual security boundary is the ``ws`` claim in the access_token
 * cookie (set by /api/auth/enter-workspace).
 *
 * Layout responsibilities:
 *   1. Require authentication + email verification (mirrors the
 *      existing (dashboard) layout).
 *   2. Require ``scope=workspace`` token. ``scope=user`` → redirect
 *      to /org (the user hasn't picked a workspace yet).
 *   3. Validate URL slug matches the token's workspace. Mismatch
 *      means a stale bookmark / link from another browser → redirect
 *      to /app/{actual-slug}/home with a notice. We don't auto-enter
 *      the URL's workspace because that could leak across tenants if
 *      a phishing link routes someone into the wrong tenant.
 */
export default function WorkspaceDashboardLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ "ws-slug": string }>;
}) {
  const { "ws-slug": wsSlug } = use(params);
  const { user, isAuthenticated, isLoading } = useAuth();
  const sessionQ = useSession();
  const workspacesQ = useWorkspaces();
  const router = useRouter();
  const pathname = usePathname();
  const isAgentChatRoute = /\/agents\/[^/]+\/chat$/.test(pathname);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  useDocumentProgress();

  // Guard 1: authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login");
  }, [isLoading, isAuthenticated, router]);

  // Guard 2: verified
  useEffect(() => {
    if (isLoading || !user) return;
    if (!user.is_verified) router.replace("/verify-email/pending");
  }, [isLoading, user, router]);

  // Guard 3: workspace-scoped token. user_token → /org.
  useEffect(() => {
    if (sessionQ.isLoading || !sessionQ.data) return;
    if (sessionQ.data.token_scope !== "workspace") {
      router.replace("/org/workspaces");
    }
  }, [sessionQ.isLoading, sessionQ.data, router]);

  // Guard 4: URL slug matches the token's ws claim. On mismatch we
  // bounce to the *correct* slug — the slug is decorative, the token
  // is authoritative, never trust the URL over the token.
  useEffect(() => {
    if (!sessionQ.data?.workspace_id || !workspacesQ.data) return;
    const tokenWs = workspacesQ.data.find(
      (w) => w.id === sessionQ.data!.workspace_id,
    );
    if (!tokenWs) return;
    if (tokenWs.slug !== wsSlug) {
      // Same path under the right slug (preserves bookmark intent).
      const rest = pathname.replace(/^\/app\/[^/]+/, "");
      router.replace(`/app/${tokenWs.slug}${rest || "/home"}`);
    }
  }, [sessionQ.data, workspacesQ.data, wsSlug, pathname, router]);

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
