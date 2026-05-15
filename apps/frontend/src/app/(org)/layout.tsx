"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth";
import { OrgLayout } from "@/features/organizations/components/OrgLayout";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";

/**
 * /org/* route group — org-level surface above any workspace.
 *
 * Auth: same gates as the dashboard (must be authenticated +
 * verified). Token scope is not enforced here — a user holding a
 * workspace_token can still browse /org to manage their org. Only
 * /app/{slug}/* (Phase 2) enforces ``scope=workspace``.
 *
 * Naming: ``/hub`` is the existing marketplace (paid template
 * store); the *organization* landing lives at ``/org``.
 */
export default function OrgRouteLayout({
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
    <OrgLayout>
      <ErrorBoundary>{children}</ErrorBoundary>
    </OrgLayout>
  );
}
