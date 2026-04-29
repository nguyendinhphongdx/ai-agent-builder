"use client";

import Link from "next/link";
import { useMemo } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Bot,
  Wrench,
  Library,
  BookOpen,
  GitBranch,
  Settings,
  MessageSquare,
  PlusSquare,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";
import { useAgents } from "@/features/agents/hooks/useAgents";
import { chatService } from "@/features/chat/services/chatService";
import { chatKeys } from "@/features/chat/hooks/useChatStream";

const AVATAR_COLORS = [
  "bg-orange-500",
  "bg-indigo-500",
  "bg-emerald-500",
  "bg-sky-500",
  "bg-pink-500",
] as const;

const navItems = [
  { href: "/hub", label: "Hub", icon: Sparkles },
  { href: "/libraries", label: "Libraries", icon: Library },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/tools", label: "Tools", icon: Wrench },
  { href: "/workflows", label: "Workflows", icon: GitBranch },
];

function NavLink({
  href, icon: Icon, label, active, collapsed,
}: {
  href: string;
  icon: React.ElementType;
  label: string;
  active: boolean;
  collapsed: boolean;
}) {
  const link = (
    <Link
      href={href}
      className={cn(
        "flex items-center rounded-lg transition-colors",
        collapsed ? "justify-center p-2" : "gap-2.5 px-3 py-1.5 text-[13px]",
        active
          ? "bg-accent text-accent-foreground font-medium"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
      )}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && label}
    </Link>
  );

  if (!collapsed) return link;

  return (
    <Tooltip>
      <TooltipTrigger asChild>{link}</TooltipTrigger>
      <TooltipContent side="right">{label}</TooltipContent>
    </Tooltip>
  );
}

interface SidebarProps {
  collapsed?: boolean;
}

export function Sidebar({ collapsed = false }: SidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentConversationId = searchParams.get("conversationId");
  const { data: agents = [] } = useAgents();
  const { data: conversations = [] } = useQuery({
    queryKey: chatKeys.conversations(),
    queryFn: () => chatService.listConversations(),
  });

  const activeAgentId = useMemo(() => {
    const match = pathname.match(/^\/agents\/([^/]+)\/chat/);
    return match?.[1] ?? null;
  }, [pathname]);

  const recentAgents = useMemo(() => {
    const byId = new Map(agents.map((a) => [a.id, a]));
    const orderedIds: string[] = [];

    for (const conv of conversations) {
      if (!orderedIds.includes(conv.agent_id)) {
        orderedIds.push(conv.agent_id);
      }
      if (orderedIds.length >= 5) break;
    }

    const picked = orderedIds
      .map((id) => byId.get(id))
      .filter((a): a is NonNullable<typeof a> => Boolean(a));

    if (picked.length < 5) {
      for (const agent of agents) {
        if (picked.find((a) => a.id === agent.id)) continue;
        picked.push(agent);
        if (picked.length >= 5) break;
      }
    }

    return picked;
  }, [agents, conversations]);

  const recentChats = useMemo(() => conversations.slice(0, 12), [conversations]);

  const initialsFromName = (name: string) =>
    name
      .split(" ")
      .map((x) => x[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

  const colorByIndex = AVATAR_COLORS;

  return (
    <aside className={cn(
      "flex h-full shrink-0 flex-col border-r border-border bg-linear-to-b from-muted/50 to-background transition-all duration-200",
      collapsed ? "w-14" : "w-64"
    )}>
      <div className={cn("flex h-14 items-center border-b border-border", collapsed ? "justify-center px-2" : "gap-2.5 px-4")}>
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary">
          <Bot className="h-3.5 w-3.5 text-primary-foreground" />
        </div>
        {!collapsed && <span className="text-sm font-semibold tracking-tight">AgentForge</span>}
      </div>

      <nav className={cn("space-y-0.5 pt-3", collapsed ? "px-1.5" : "p-2")}>
        {navItems.map((item) => (
          <NavLink key={item.href} href={item.href} icon={item.icon} label={item.label}
            active={pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))}
            collapsed={collapsed} />
        ))}
        <NavLink href="/chat/new" icon={PlusSquare} label="New Chat"
          active={pathname === "/chat/new"} collapsed={collapsed} />
      </nav>

      {!collapsed && (
        <>
          <div className="mx-2 mb-2 border-t border-border" />

          <div className="scrollbar-thin flex-1 overflow-auto px-2 pb-2">
            <div className="mb-2 px-2 text-xs font-semibold text-foreground">Recent</div>
            <div className="space-y-0.5">
              {recentAgents.map((agent, idx) => {
                const isActive = activeAgentId === agent.id;
                return (
                  <Link
                    key={agent.id}
                    href={`/agents/${agent.id}/chat`}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] transition-colors",
                      isActive
                        ? "bg-sky-500/15 text-sky-700 dark:text-sky-300 ring-1 ring-sky-500/25"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )}
                  >
                    <span
                      className={cn(
                        "inline-flex h-5 w-5 shrink-0 items-center justify-center rounded text-[10px] font-semibold text-white",
                        colorByIndex[idx % colorByIndex.length]
                      )}
                    >
                      {initialsFromName(agent.name)}
                    </span>
                    <span className="truncate">{agent.name}</span>
                  </Link>
                );
              })}
            </div>

            <div className="my-2 border-t border-border" />
            <div className="mb-2 px-2 text-xs font-semibold text-foreground">Chats</div>
            <div className="space-y-0.5">
              {recentChats.map((conv) => {
                const isActive = currentConversationId === conv.id;
                const label = conv.title?.trim() || "New conversation";
                return (
                  <Link
                    key={conv.id}
                    href={`/agents/${conv.agent_id}/chat?conversationId=${conv.id}`}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-1.5 text-[13px] transition-colors",
                      isActive
                        ? "bg-sky-500/15 text-sky-700 dark:text-sky-300 ring-1 ring-sky-500/25"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )}
                    title={label}
                  >
                    <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </>
      )}

      {collapsed && <div className="flex-1" />}

      <div className={cn("border-t border-border", collapsed ? "p-1.5" : "p-2")}>
        <NavLink href="/settings" icon={Settings} label="Settings"
          active={pathname.startsWith("/settings")} collapsed={collapsed} />
      </div>
    </aside>
  );
}
