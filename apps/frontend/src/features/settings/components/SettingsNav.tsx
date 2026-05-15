"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "@/lib/i18n/context";
import {
  Banknote,
  ShieldCheck,
  SlidersHorizontal,
  User as UserIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  labelKey: string;
  icon: React.ElementType;
}

/**
 * User-level settings only.
 *
 * Workspace-scoped settings (credentials, API tokens, integrations,
 * connections, usage, feedback, workspace name + members + quota)
 * live at ``/ws/settings`` — they need a workspace_token. Org-scoped
 * settings (members, billing, plan, security policies) live at
 * ``/org/*``.
 *
 * What stays here:
 *   - Profile (avatar, name, email)
 *   - Security (password, MFA, sessions)
 *   - Preferences (locale, theme)
 *   - Payouts (author's Stripe Connect — user-level so creators can
 *     receive payouts independent of any workspace they belong to)
 */
const ITEMS: NavItem[] = [
  { href: "/settings/profile", labelKey: "settings.profile", icon: UserIcon },
  { href: "/settings/security", labelKey: "settings.security", icon: ShieldCheck },
  { href: "/settings/preferences", labelKey: "settings.preferences", icon: SlidersHorizontal },
  { href: "/settings/payouts", labelKey: "settings.payouts", icon: Banknote },
];

export function SettingsNav() {
  const pathname = usePathname();
  const { t } = useTranslations();

  return (
    <nav aria-label="Settings sections">
      <ul className="space-y-0.5">
        {ITEMS.map((item) => {
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
    </nav>
  );
}
