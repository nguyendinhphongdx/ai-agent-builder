"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth";
import { HubLayout } from "@/features/hub/components/HubLayout";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

/**
 * /hub/* route group — org-level surface above any workspace.
 *
 * Auth: same gates as the dashboard (must be authenticated +
 * verified). Token scope is not enforced here — a user holding a
 * workspace_token can still browse /hub to manage their org. Only
 * /app/{slug}/* (Phase 2) enforces ``scope=workspace``.
 */
export default function HubRouteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login");
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isLoading || !user) return;
    if (!user.is_verified) router.replace("/verify-email/pending");
  }, [isLoading, user, router]);

  if (isLoading || !isAuthenticated || (user && !user.is_verified)) {
    return (
      <div className="flex h-[100dvh] items-center justify-center bg-background">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-muted border-t-foreground" />
      </div>
    );
  }

  return (
    <HubLayout>
      <ErrorBoundary>{children}</ErrorBoundary>
    </HubLayout>
  );
}
