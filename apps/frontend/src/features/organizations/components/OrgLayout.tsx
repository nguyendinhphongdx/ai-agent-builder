"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bot, Building2, CreditCard, Layers, ShieldCheck, Users } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { organizationsService } from "@/lib/api/organizationsService";
import { cn } from "@/lib/utils";

/**
 * Org shell — org-level surface (path: /org/*). Sidebar lists the
 * org-scoped tabs (Workspaces, Members, Billing, Security, Audit,
 * Settings); top holds the brand + org switcher when the user
 * belongs to many orgs.
 *
 * Distinct from the workspace dashboard layout: no workspace
 * switcher here (you're *above* a workspace), no per-workspace
 * resources (agents, chat, …).
 *
 * Naming: the existing /hub path belongs to the *marketplace* (paid
 * template store). This page is the *organization* landing — hence
 * /org and not /hub.
 */

const NAV: Array<{ href: string; label: string; icon: React.ElementType }> = [
  { href: "/org/workspaces", label: "Workspaces", icon: Layers },
  // Phase 4 — placeholders so the sidebar shape is stable.
  { href: "/org/members", label: "Members", icon: Users },
  { href: "/org/billing", label: "Billing", icon: CreditCard },
  { href: "/org/security", label: "Security", icon: ShieldCheck },
  { href: "/org/settings", label: "Settings", icon: Building2 },
];

export function OrgLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const orgsQ = useQuery({
    queryKey: ["organizations"],
    queryFn: () => organizationsService.list(),
    staleTime: 60_000,
  });
  const orgs = orgsQ.data ?? [];
  // For Phase 1 we operate on the first org. Phase 5 adds the org
  // switcher and reads the active org from a context/store.
  const activeOrg = orgs[0];

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background text-foreground">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-muted/20">
        <div className="border-b border-border px-5 py-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <span className="text-sm font-bold tracking-tight">AgentForge</span>
          </Link>
          <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Organization
          </p>
          <p className="mt-0.5 truncate text-sm font-medium">
            {orgsQ.isLoading ? "…" : activeOrg?.name ?? "No organization"}
          </p>
          {activeOrg && (
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {activeOrg.plan} · {activeOrg.role}
            </p>
          )}
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] transition-colors",
                  active
                    ? "bg-accent font-medium text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border p-3 text-[11px] text-muted-foreground">
          <Link
            href="/home"
            className="block rounded-md px-2 py-1.5 transition-colors hover:bg-accent hover:text-foreground"
          >
            ← Back to workspace
          </Link>
          <Link
            href="/hub"
            className="mt-1 block rounded-md px-2 py-1.5 transition-colors hover:bg-accent hover:text-foreground"
          >
            Browse marketplace →
          </Link>
        </div>
      </aside>

      <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}

/** Hook used by Hub pages so each can get the active org id without
 *  drilling props through the layout. Phase 5 will swap this for an
 *  org-context store. */
export function useActiveOrg() {
  const orgsQ = useQuery({
    queryKey: ["organizations"],
    queryFn: () => organizationsService.list(),
    staleTime: 60_000,
  });
  return {
    org: orgsQ.data?.[0] ?? null,
    isLoading: orgsQ.isLoading,
    orgs: orgsQ.data ?? [],
  };
}
