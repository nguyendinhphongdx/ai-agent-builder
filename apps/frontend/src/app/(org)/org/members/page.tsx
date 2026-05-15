"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  organizationsService,
  type OrgRole,
} from "@/lib/api/organizationsService";
import { useActiveOrg } from "@/features/organizations/components/OrgLayout";

/**
 * Org → Members tab.
 *
 * BE limitation (Phase 4a): invite-by-email only works for users
 * who already have an AgentForge account — BE returns 404 otherwise.
 * Magic-link invitation flow with an ``organization_invitations``
 * table lands in a later phase. For now the UI surfaces the error
 * so the inviter knows what happened.
 *
 * Role hierarchy: owner > admin > editor > viewer. Owners can
 * promote/demote everyone; admins can manage editors/viewers but
 * not other owners (BE enforces; FE shows the choices read-only
 * when the current user lacks permission).
 */
const ROLE_OPTIONS: OrgRole[] = ["viewer", "editor", "admin", "owner"];
const INVITE_ROLE_OPTIONS: OrgRole[] = ["viewer", "editor", "admin"];

export default function OrgMembersPage() {
  const { org, isLoading: orgLoading } = useActiveOrg();
  const qc = useQueryClient();

  const membersQ = useQuery({
    queryKey: ["organizations", org?.id, "members"],
    queryFn: () => organizationsService.listMembers(org!.id),
    enabled: !!org,
  });

  const invite = useMutation({
    mutationFn: ({ email, role }: { email: string; role: OrgRole }) =>
      organizationsService.inviteMember(org!.id, { email, role }),
    onSuccess: () => {
      toast.success("Member invited");
      qc.invalidateQueries({ queryKey: ["organizations", org!.id, "members"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const changeRole = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: OrgRole }) =>
      organizationsService.updateMemberRole(org!.id, userId, role),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["organizations", org!.id, "members"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const remove = useMutation({
    mutationFn: (userId: string) =>
      organizationsService.removeMember(org!.id, userId),
    onSuccess: () => {
      toast.success("Member removed");
      qc.invalidateQueries({ queryKey: ["organizations", org!.id, "members"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  if (orgLoading || !org) return <Spinner />;

  const canManage = org.role === "owner" || org.role === "admin";

  return (
    <div className="mx-auto max-w-4xl px-6 py-10 lg:px-8">
      <header className="flex items-start justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Members</h1>
          <p className="mt-1 max-w-xl text-xs text-muted-foreground">
            Mỗi thành viên có 1 role ở org. Role này tự động áp dụng cho mọi
            workspace bên trong: org-admin/owner = workspace-admin/owner ở mọi
            workspace mà không cần thêm vào từng workspace.
          </p>
        </div>
        {canManage && <InviteButton orgId={org.id} loading={invite.isPending} onInvite={invite.mutate} />}
      </header>

      <section className="mt-6">
        {membersQ.isLoading ? (
          <Spinner />
        ) : (membersQ.data ?? []).length === 0 ? (
          <Empty>Chỉ có 1 mình bạn trong org.</Empty>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-card">
            {(membersQ.data ?? []).map((m) => (
              <li
                key={m.user_id}
                className="flex items-center gap-3 px-5 py-3 text-xs"
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium uppercase">
                  {(m.full_name || m.email).slice(0, 2)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">
                    {m.full_name || m.email}
                  </div>
                  {m.full_name && (
                    <div className="truncate text-[10px] text-muted-foreground">
                      {m.email}
                    </div>
                  )}
                </div>
                {canManage && m.role !== "owner" ? (
                  <select
                    value={m.role}
                    onChange={(e) =>
                      changeRole.mutate({
                        userId: m.user_id,
                        role: e.target.value as OrgRole,
                      })
                    }
                    disabled={changeRole.isPending}
                    className="h-7 rounded-md border border-border bg-background px-2 text-[11px]"
                  >
                    {ROLE_OPTIONS.map((r) => (
                      <option
                        key={r}
                        value={r}
                        disabled={r === "owner" && org.role !== "owner"}
                      >
                        {r}
                      </option>
                    ))}
                  </select>
                ) : (
                  <Badge variant="outline" className="text-[10px]">
                    {m.role}
                  </Badge>
                )}
                {canManage && m.role !== "owner" && (
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => {
                      if (
                        window.confirm(
                          `Remove ${m.full_name || m.email} from the organization?`,
                        )
                      ) {
                        remove.mutate(m.user_id);
                      }
                    }}
                    disabled={remove.isPending}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

/* ─── Invite dialog ────────────────────────────────────────────── */

function InviteButton({
  loading,
  onInvite,
}: {
  orgId: string;
  loading: boolean;
  onInvite: (body: { email: string; role: OrgRole }) => void;
}) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrgRole>("editor");

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus className="mr-1.5 h-3.5 w-3.5" />
        Invite member
      </Button>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-full max-w-md rounded-lg border border-border bg-card p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-semibold">Invite member</h2>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Chỉ invite được user đã có tài khoản AgentForge — magic-link
              invitation cho user mới sẽ thêm sau.
            </p>
            <div className="mt-4 space-y-3">
              <div className="space-y-1">
                <Label htmlFor="org-invite-email" className="text-[11px]">
                  Email
                </Label>
                <Input
                  id="org-invite-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="user@example.com"
                  autoFocus
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="org-invite-role" className="text-[11px]">
                  Role
                </Label>
                <select
                  id="org-invite-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as OrgRole)}
                  className="h-9 w-full rounded-md border border-border bg-background px-2 text-xs"
                >
                  {INVITE_ROLE_OPTIONS.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-muted-foreground">
                  Owner role phải promote từ existing member, không invite trực
                  tiếp.
                </p>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={!email.trim() || loading}
                onClick={() => {
                  onInvite({ email: email.trim(), role });
                  setEmail("");
                  setOpen(false);
                }}
              >
                {loading ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  "Invite"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ─── Helpers ──────────────────────────────────────────────────── */

function Spinner() {
  return (
    <div className="flex h-32 items-center justify-center">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-border p-8 text-center text-xs text-muted-foreground">
      {children}
    </div>
  );
}

function extractMsg(err: unknown): string {
  const anyErr = err as {
    response?: { data?: { detail?: string | object } };
    message?: string;
  };
  const detail = anyErr?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return anyErr?.message ?? "Request failed";
}
