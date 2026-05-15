"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  BarChart3,
  ChevronDown,
  Key,
  KeyRound,
  Link2,
  Plug,
  SlidersHorizontal,
  ThumbsUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Workspace-settings shell.
 *
 * Groups items into collapsible sections so a workspace admin can
 * scan by purpose: General/Members (who) → Resources (credentials,
 * tokens) → Channels (integrations, connections) → Insights (usage,
 * feedback).
 *
 * Groups default to expanded; click the chevron to collapse. State
 * is in-memory only — refreshing re-expands everything, which is the
 * less-surprising default for a settings page.
 */

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const GROUPS: NavGroup[] = [
  {
    title: "Workspace",
    items: [
      { href: "/ws/settings", label: "General & members", icon: SlidersHorizontal },
    ],
  },
  {
    title: "Resources",
    items: [
      { href: "/ws/settings/credentials", label: "AI credentials", icon: Key },
      { href: "/ws/settings/api-tokens", label: "API tokens", icon: KeyRound },
    ],
  },
  {
    title: "Channels",
    items: [
      { href: "/ws/settings/integrations", label: "Integrations", icon: Plug },
      { href: "/ws/settings/connections", label: "Connections", icon: Link2 },
    ],
  },
  {
    title: "Insights",
    items: [
      { href: "/ws/settings/usage", label: "Usage & cost", icon: BarChart3 },
      { href: "/ws/settings/annotations", label: "Feedback", icon: ThumbsUp },
    ],
  },
];

export default function WorkspaceSettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="mx-auto flex w-full max-w-6xl gap-8 p-6">
      <aside className="w-56 shrink-0">
        <h1 className="mb-4 px-2 text-base font-semibold tracking-tight">
          Workspace settings
        </h1>
        <nav aria-label="Workspace settings sections" className="space-y-3">
          {GROUPS.map((group) => (
            <Group key={group.title} group={group} pathname={pathname} />
          ))}
        </nav>
      </aside>
      <main className="min-w-0 flex-1">{children}</main>
    </div>
  );
}

function Group({ group, pathname }: { group: NavGroup; pathname: string }) {
  // Auto-expand if the active route lives inside this group, so a
  // direct deep-link doesn't land on a collapsed parent.
  const containsActive = group.items.some(
    (i) => pathname === i.href || pathname.startsWith(i.href + "/"),
  );
  const [open, setOpen] = useState(true);
  const expanded = open || containsActive;

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground"
      >
        <span>{group.title}</span>
        <ChevronDown
          className={cn(
            "h-3 w-3 transition-transform",
            expanded ? "" : "-rotate-90",
          )}
        />
      </button>
      {expanded && (
        <ul className="mt-1 space-y-0.5">
          {group.items.map((item) => {
            const Icon = item.icon;
            // For /ws/settings (General) we want exact match — other
            // items prefix-match so deep routes light their parent.
            const active =
              item.href === "/ws/settings"
                ? pathname === item.href
                : pathname === item.href || pathname.startsWith(item.href + "/");
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
      )}
    </div>
  );
}
