"use client";

import Link from "next/link";
import { Banknote, ChevronUp, LogOut, Settings, User as UserIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAuth, useLogout } from "@/features/auth/hooks/useAuth";

/**
 * User dropdown rendered as a row at the bottom of a sidebar.
 *
 * Replaces the floating avatar that org / system layouts had — those
 * pages don't include the top Header, so the only way to get to
 * Profile / Settings / Sign out was to click through to /ws. This
 * component bridges that gap with the same menu items as the Header
 * dropdown (minus workspace-specific entries).
 */
export function SidebarUserMenu() {
  const { user } = useAuth();
  const logout = useLogout();

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? "U";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left transition-colors hover:bg-accent/50"
          aria-label="Account menu"
        >
          <Avatar className="h-7 w-7 shrink-0">
            {user?.avatar_url && <AvatarImage src={user.avatar_url} />}
            <AvatarFallback className="bg-muted text-[10px]">{initials}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-foreground">
              {user?.full_name ?? "Unnamed"}
            </p>
            <p className="truncate text-[10px] text-muted-foreground">
              {user?.email}
            </p>
          </div>
          <ChevronUp className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="top" align="start" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5 py-2">
          <span className="text-sm font-medium">{user?.full_name ?? "Unnamed"}</span>
          <span className="truncate text-[11px] font-normal text-muted-foreground">
            {user?.email}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/settings/profile" className="cursor-pointer">
            <UserIcon className="mr-2 h-3.5 w-3.5" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/ws/settings" className="cursor-pointer">
            <Settings className="mr-2 h-3.5 w-3.5" />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/settings/payouts" className="cursor-pointer">
            <Banknote className="mr-2 h-3.5 w-3.5" />
            Payouts
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => logout.mutate()}
          className="text-destructive focus:text-destructive"
        >
          <LogOut className="mr-2 h-3.5 w-3.5" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
