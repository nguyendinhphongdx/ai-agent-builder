"use client";

import { useState } from "react";
import { Loader2, Mail, ShieldCheck, ShieldOff } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAdminUsers, useBanUser, useGrantRole } from "../hooks/useAdmin";
import {
  hasRole,
  type AdminUserRow,
  type UserRole,
  ROLE_HIERARCHY,
} from "../types";

interface UsersTabProps {
  currentRole: string;
}

export function UsersTab({ currentRole }: UsersTabProps) {
  const [q, setQ] = useState("");
  const { data: users, isLoading } = useAdminUsers({ q: q || undefined });

  return (
    <div className="space-y-4">
      <Input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search email..."
        className="max-w-xs text-xs"
      />

      {isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : !users || users.length === 0 ? (
        <p className="rounded-xl border border-dashed border-border bg-card py-12 text-center text-xs text-muted-foreground">
          No users.
        </p>
      ) : (
        <div className="space-y-2">
          {users.map((u) => (
            <UserRowCard key={u.id} user={u} canGrantRole={hasRole(currentRole, "admin")} />
          ))}
        </div>
      )}
    </div>
  );
}

function UserRowCard({
  user,
  canGrantRole,
}: {
  user: AdminUserRow;
  canGrantRole: boolean;
}) {
  const ban = useBanUser();
  const grant = useGrantRole();

  const toggleBan = () => {
    if (
      user.is_active &&
      !window.confirm(`Ban ${user.email}? They will be logged out immediately.`)
    ) {
      return;
    }
    ban.mutate({ id: user.id, body: { is_active: !user.is_active } });
  };

  const setRole = (role: UserRole) => {
    if (role === user.role) return;
    grant.mutate({ id: user.id, body: { role } });
  };

  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-card p-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted">
        <Mail className="h-4 w-4 text-muted-foreground" />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-semibold">{user.email}</span>
          {user.is_verified && (
            <ShieldCheck className="h-3 w-3 text-emerald-500" aria-label="Verified" />
          )}
          {!user.is_active && (
            <Badge variant="outline" className="text-[10px] text-red-600 border-red-500/40">
              Banned
            </Badge>
          )}
          <RoleBadge role={user.role} />
        </div>
        <p className="text-[11px] text-muted-foreground">
          {user.full_name ?? "—"} · joined {new Date(user.created_at).toLocaleDateString()}
        </p>
      </div>

      <div className="flex items-center gap-1 shrink-0">
        {canGrantRole && (
          <select
            value={user.role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            disabled={grant.isPending}
            className="rounded-md border border-border bg-background px-2 py-1 text-xs"
          >
            {ROLE_HIERARCHY.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        )}
        <Button
          variant={user.is_active ? "outline" : "default"}
          size="sm"
          className="gap-1.5"
          onClick={toggleBan}
          disabled={ban.isPending}
        >
          <ShieldOff className="h-3 w-3" />
          {user.is_active ? "Ban" : "Unban"}
        </Button>
      </div>
    </div>
  );
}

function RoleBadge({ role }: { role: string }) {
  if (role === "user") return null;
  const colours: Record<string, string> = {
    moderator: "border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300",
    support: "border-purple-500/40 bg-purple-500/10 text-purple-700 dark:text-purple-300",
    admin: "border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-300",
  };
  return (
    <Badge variant="outline" className={`text-[10px] ${colours[role] ?? ""}`}>
      {role}
    </Badge>
  );
}
