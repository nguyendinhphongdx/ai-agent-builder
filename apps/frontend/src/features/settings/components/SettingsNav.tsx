"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Banknote,
  Building2,
  Key,
  KeyRound,
  Plug,
  ShieldCheck,
  SlidersHorizontal,
  User as UserIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

/**
 * Three groups so power users can scan the sidebar by purpose:
 * - Account: things about *you*.
 * - Workspace: keys + tokens + integrations needed to operate agents.
 * - Marketplace: only relevant once you publish on the Hub.
 */
const GROUPS: NavGroup[] = [
  {
    title: "Account",
    items: [
      { href: "/settings/profile", label: "Profile", icon: UserIcon },
      { href: "/settings/security", label: "Security", icon: ShieldCheck },
      { href: "/settings/preferences", label: "Preferences", icon: SlidersHorizontal },
    ],
  },
  {
    title: "Workspace",
    items: [
      { href: "/settings/workspace", label: "Workspace", icon: Building2 },
      { href: "/settings/credentials", label: "AI Credentials", icon: Key },
      { href: "/settings/api-tokens", label: "API Tokens", icon: KeyRound },
      { href: "/settings/integrations", label: "Integrations", icon: Plug },
    ],
  },
  {
    title: "Marketplace",
    items: [{ href: "/settings/payouts", label: "Author Payouts", icon: Banknote }],
  },
];

/** Vertical nav for the Settings layout — each item is a Next.js Link
 *  so the active sub-route is deep-linkable and survives refresh. */
export function SettingsNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Settings sections" className="space-y-5">
      {GROUPS.map((group) => (
        <div key={group.title}>
          <h2 className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {group.title}
          </h2>
          <ul className="space-y-0.5">
            {group.items.map((item) => {
              const Icon = item.icon;
              const active =
                pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2.5 rounded-md px-2 py-1.5 text-[13px] transition-colors",
                      active
                        ? "bg-accent font-medium text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                    )}
                  >
                    <Icon className="h-3.5 w-3.5 shrink-0" />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
