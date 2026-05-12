"use client";

import Link from "next/link";
import { useTheme } from "next-themes";
import {
  Banknote,
  Home,
  LogOut,
  Monitor,
  Moon,
  PanelLeft,
  PanelLeftClose,
  Settings,
  Sun,
  User as UserIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { LocaleSwitcher } from "@/components/LocaleSwitcher";
import { useAuth, useLogout } from "@/features/auth/hooks/useAuth";
import { NotificationBell } from "@/features/notifications/components/NotificationBell";
import { WorkspaceSwitcher } from "@/features/workspaces/components/WorkspaceSwitcher";

interface HeaderProps {
  sidebarOpen?: boolean;
  onToggleSidebar?: () => void;
}

export function Header({ sidebarOpen = true, onToggleSidebar }: HeaderProps) {
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
    <header className="flex h-12 items-center gap-2 border-b border-border bg-background px-3">
      {onToggleSidebar && (
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggleSidebar}
          className="text-muted-foreground hover:text-foreground"
        >
          {sidebarOpen ? (
            <PanelLeftClose className="h-4 w-4" />
          ) : (
            <PanelLeft className="h-4 w-4" />
          )}
        </Button>
      )}

      <WorkspaceSwitcher />

      <div className="flex-1" />

      <NotificationBell />

      <LocaleSwitcher />

      <ThemeToggle />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="relative h-7 w-7 rounded-full"
            aria-label="Account menu"
          >
            <Avatar className="h-7 w-7">
              {user?.avatar_url && <AvatarImage src={user.avatar_url} />}
              <AvatarFallback className="bg-muted text-[11px]">{initials}</AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="flex flex-col gap-0.5 py-2">
            <span className="text-sm font-medium">
              {user?.full_name ?? "Unnamed"}
            </span>
            <span className="truncate text-[11px] font-normal text-muted-foreground">
              {user?.email}
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/home" className="cursor-pointer">
              <Home className="mr-2 h-3.5 w-3.5" />
              Home
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/settings/profile" className="cursor-pointer">
              <UserIcon className="mr-2 h-3.5 w-3.5" />
              Profile
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/settings" className="cursor-pointer">
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
    </header>
  );
}

/** Theme toggle with three explicit options (light · dark · system) so
 *  users on a managed device can opt into following the OS preference. */
function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const next =
    theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
  const Icon = theme === "dark" ? Moon : theme === "system" ? Monitor : Sun;
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(next)}
      className="h-8 w-8"
      aria-label={`Switch to ${next} theme (currently ${theme ?? "light"})`}
      title={`Theme: ${theme ?? "light"} — click for ${next}`}
    >
      <Icon className="h-4 w-4" />
    </Button>
  );
}
