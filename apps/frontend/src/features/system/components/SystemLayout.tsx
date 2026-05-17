"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useEffect } from "react";
import {
  Bot,
  Building2,
  CreditCard,
  FileText,
  LayoutDashboard,
  Loader2,
  Package,
  ShieldOff,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSystemAccess } from "../hooks/useSystemAccess";

/**
 * Shell for ``/system/*`` — the Base.vn-style platform-owner surface.
 *
 * Gate: only renders for members of the org with ``is_system=true``.
 * Non-members are bounced to ``/ws/home`` so the route is effectively
 * invisible from the rest of the app's nav.
 */

type NavItem = {
  href: string;
  label: string;
  icon: React.ElementType;
  disabled?: boolean;
};

const NAV: readonly NavItem[] = [
  { href: "/system/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/system/organizations", label: "Organizations", icon: Building2 },
  { href: "/system/subscriptions", label: "Subscriptions", icon: CreditCard },
  { href: "/system/packages", label: "Packages", icon: Package },
  { href: "/system/contracts", label: "Contracts", icon: FileText, disabled: true },
];

export function SystemLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { isLoading, isMember, systemOrg } = useSystemAccess();

  useEffect(() => {
    if (!isLoading && !isMember) {
      router.replace("/ws/home");
    }
  }, [isLoading, isMember, router]);

  if (isLoading) {
    return (
      <div className="flex h-dvh items-center justify-center bg-background">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!isMember) {
    return (
      <div className="flex h-dvh items-center justify-center bg-background text-center">
        <div className="space-y-2">
          <ShieldOff className="mx-auto h-6 w-6 text-muted-foreground" />
          <p className="text-sm font-medium">Platform admin only</p>
          <p className="text-xs text-muted-foreground">Redirecting…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-dvh overflow-hidden bg-background text-foreground">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-muted/20">
        <div className="border-b border-border px-5 py-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <span className="text-sm font-bold tracking-tight">AgentForge</span>
          </Link>
          <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-primary">
            Platform
          </p>
          <p className="mt-0.5 truncate text-sm font-medium">
            {systemOrg?.name ?? "System"}
          </p>
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
            {systemOrg?.role ?? "—"}
          </p>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            if (item.disabled) {
              return (
                <span
                  key={item.href}
                  className="flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] text-muted-foreground/50"
                  title="Coming soon"
                >
                  <Icon className="h-3.5 w-3.5 shrink-0" />
                  <span>{item.label}</span>
                  <span className="ml-auto rounded bg-muted px-1.5 py-0.5 text-[9px] uppercase tracking-wider">
                    soon
                  </span>
                </span>
              );
            }
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
            href="/ws/home"
            className="block rounded-md px-2 py-1.5 transition-colors hover:bg-accent hover:text-foreground"
          >
            ← Back to workspace
          </Link>
        </div>
      </aside>

      <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
