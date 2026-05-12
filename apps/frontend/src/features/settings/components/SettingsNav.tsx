"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "@/lib/i18n/context";
import {
  Banknote,
  BarChart3,
  Building2,
  CreditCard,
  Key,
  KeyRound,
  Link2,
  Plug,
  ShieldCheck,
  SlidersHorizontal,
  ThumbsUp,
  Zap,
  User as UserIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  labelKey: string;
  icon: React.ElementType;
}

interface NavGroup {
  titleKey: string;
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
    titleKey: "settings.account",
    items: [
      { href: "/settings/profile", labelKey: "settings.profile", icon: UserIcon },
      { href: "/settings/security", labelKey: "settings.security", icon: ShieldCheck },
      { href: "/settings/preferences", labelKey: "settings.preferences", icon: SlidersHorizontal },
    ],
  },
  {
    titleKey: "settings.workspace",
    items: [
      { href: "/settings/workspace", labelKey: "settings.workspace", icon: Building2 },
      { href: "/settings/credentials", labelKey: "settings.credentials", icon: Key },
      { href: "/settings/api-tokens", labelKey: "settings.apiTokens", icon: KeyRound },
      { href: "/settings/integrations", labelKey: "settings.integrations", icon: Plug },
      { href: "/settings/connections", labelKey: "settings.connections", icon: Link2 },
      { href: "/settings/triggers", labelKey: "settings.triggers", icon: Zap },
      { href: "/settings/usage", labelKey: "settings.usage", icon: BarChart3 },
      { href: "/settings/billing", labelKey: "settings.billing", icon: CreditCard },
      { href: "/settings/annotations", labelKey: "settings.feedback", icon: ThumbsUp },
    ],
  },
  {
    titleKey: "settings.marketplace",
    items: [{ href: "/settings/payouts", labelKey: "settings.payouts", icon: Banknote }],
  },
];

/** Vertical nav for the Settings layout — each item is a Next.js Link
 *  so the active sub-route is deep-linkable and survives refresh. */
export function SettingsNav() {
  const pathname = usePathname();
  const { t } = useTranslations();

  return (
    <nav aria-label="Settings sections" className="space-y-5">
      {GROUPS.map((group) => (
        <div key={group.titleKey}>
          <h2 className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {t(group.titleKey)}
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
                    <span>{t(item.labelKey)}</span>
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
