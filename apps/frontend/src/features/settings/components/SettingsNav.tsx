"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Banknote,
  Key,
  KeyRound,
  Plug,
  Settings as SettingsIcon,
  SlidersHorizontal,
  User as UserIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  description?: string;
}

const ITEMS: NavItem[] = [
  {
    href: "/settings/profile",
    label: "Profile",
    icon: UserIcon,
    description: "Your name + avatar",
  },
  {
    href: "/settings/preferences",
    label: "Preferences",
    icon: SlidersHorizontal,
    description: "Theme + defaults",
  },
  {
    href: "/settings/credentials",
    label: "AI Credentials",
    icon: Key,
    description: "LLM provider keys",
  },
  {
    href: "/settings/api-tokens",
    label: "API Tokens",
    icon: KeyRound,
    description: "External clients",
  },
  {
    href: "/settings/integrations",
    label: "Integrations",
    icon: Plug,
    description: "Channels + embeds",
  },
  {
    href: "/settings/payouts",
    label: "Author Payouts",
    icon: Banknote,
    description: "Connect + history",
  },
];

/** Vertical nav for the Settings layout — each item is a Next.js Link
 *  so the active sub-route is deep-linkable and survives refresh, unlike
 *  in-component tab state. */
export function SettingsNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Settings sections" className="space-y-0.5">
      <header className="mb-3 flex items-center gap-2 px-2 py-1">
        <SettingsIcon className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm font-semibold">Settings</span>
      </header>

      {ITEMS.map((item) => {
        const Icon = item.icon;
        // Match by prefix so nested sub-routes (e.g. /settings/integrations/api-docs)
        // still highlight their parent.
        const active =
          pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex items-start gap-2.5 rounded-md px-2 py-1.5 text-[13px] transition-colors",
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
            )}
          >
            <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <div className="flex-1">
              <div className={cn("font-medium", active && "text-foreground")}>
                {item.label}
              </div>
              {item.description && (
                <div className="text-[10px] text-muted-foreground/70">
                  {item.description}
                </div>
              )}
            </div>
          </Link>
        );
      })}
    </nav>
  );
}
