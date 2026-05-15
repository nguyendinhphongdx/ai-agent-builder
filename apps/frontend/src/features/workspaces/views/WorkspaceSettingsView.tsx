"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import {
  useWorkspaces,
  useUpdateWorkspace,
  useDeleteWorkspace,
  useWorkspaceMembers,
  useAddableWorkspaceMembers,
  useAddWorkspaceMember,
  useUpdateMemberRole,
  useRemoveMember,
} from "../hooks/useWorkspaces";
import { RoleInspector } from "../components/RoleInspector";
import { useSession } from "../hooks/useWorkspaceSession";
import { roleAtLeast, type WorkspaceRole } from "../types";

const ROLE_OPTIONS: WorkspaceRole[] = ["viewer", "editor", "admin", "owner"];
const ADD_ROLE_OPTIONS: WorkspaceRole[] = ["viewer", "editor", "admin"];

export function WorkspaceSettingsView() {
  const router = useRouter();
  const { data: workspaces } = useWorkspaces();
  const sessionQ = useSession();
  const currentId = sessionQ.data?.workspace_id ?? null;
  const current = workspaces?.find((w) => w.id === currentId) ?? null;

  if (!current) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-muted-foreground">
        <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
        Loading workspace…
      </div>
    );
  }

  if (current.is_personal) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <SettingsPageHeader
          title="Workspace settings"
          description="Personal workspaces không có member management — gắn liền với account của bạn."
        />
        <SettingsCard>
          <div className="p-5 text-xs text-muted-foreground">
            <p>
              Bạn đang ở workspace <strong>{current.name}</strong> — đây là
              personal workspace. Nếu muốn collaborate với người khác, hãy tạo
              team workspace mới qua header switcher.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-3"
              onClick={() => router.push("/settings")}
            >
              Back to settings
            </Button>
          </div>
        </SettingsCard>
      </div>
    );
  }

  const canManage = roleAtLeast(current.role, "admin");
  const canDelete = current.role === "owner";

  return (
    <div className="mx-auto max-w-4xl p-6">
      <SettingsPageHeader
        title={current.name}
        description={`Workspace ${current.slug} · ${current.organization.name} · bạn là ${current.role}`}
      />
      <Tabs defaultValue="members" className="w-full">
        <TabsList>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="roles">Roles</TabsTrigger>
          {canManage && <TabsTrigger value="quota">Quota</TabsTrigger>}
          {canManage && <TabsTrigger value="general">General</TabsTrigger>}
          {canDelete && (
            <TabsTrigger value="danger" className="text-destructive">
              Danger zone
            </TabsTrigger>
          )}
        </TabsList>

        <TabsContent value="members" className="mt-4">
          <MembersPanel workspaceId={current.id} myRole={current.role} />
        </TabsContent>

        <TabsContent value="roles" className="mt-4">
          <SettingsCard
            title="Built-in roles"
            description="What each role can do. Expand to see the permission set."
          >
            <div className="p-5">
              <RoleInspector />
            </div>
          </SettingsCard>
        </TabsContent>

        {canManage && (
          <TabsContent value="quota" className="mt-4">
            <QuotaPanel workspace={current} />
          </TabsContent>
        )}

        {canManage && (
          <TabsContent value="general" className="mt-4">
            <GeneralPanel workspaceId={current.id} name={current.name} />
          </TabsContent>
        )}

        {canDelete && (
          <TabsContent value="danger" className="mt-4">
            <DangerZonePanel workspaceId={current.id} name={current.name} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

/* ─── Members ───────────────────────────────────────────────────── */

function MembersPanel({
  workspaceId,
  myRole,
}: {
  workspaceId: string;
  myRole: WorkspaceRole;
}) {
  const { data: members, isLoading } = useWorkspaceMembers(workspaceId);
  const updateRole = useUpdateMemberRole(workspaceId);
  const remove = useRemoveMember(workspaceId);
  const canManage = roleAtLeast(myRole, "admin");

  const handleRoleChange = async (userId: string, role: WorkspaceRole) => {
    try {
      await updateRole.mutateAsync({ userId, role });
      toast.success("Role updated");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  const handleRemove = async (userId: string) => {
    if (!confirm("Remove this member?")) return;
    try {
      await remove.mutateAsync(userId);
      toast.success("Member removed");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  return (
    <SettingsStack>
      {canManage && <AddMemberCard workspaceId={workspaceId} />}
      <SettingsCard
        title="Members"
        description={
          canManage
            ? "Quản lý role + remove members."
            : "Bạn chỉ xem được — admin+ mới quản lý được role."
        }
      >
        {isLoading ? (
          <SkeletonRows />
        ) : !members || members.length === 0 ? (
          <Empty>Chưa có member.</Empty>
        ) : (
          <ul className="divide-y divide-border">
            {members.map((m) => (
              <li
                key={m.user_id}
                className="flex items-center gap-3 px-5 py-3 text-xs"
              >
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium uppercase">
                  {(m.user.full_name || m.user.email).slice(0, 2)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">
                    {m.user.full_name || m.user.email}
                  </div>
                  {m.user.full_name && (
                    <div className="truncate text-[10px] text-muted-foreground">
                      {m.user.email}
                    </div>
                  )}
                </div>
                {canManage ? (
                  <Select
                    value={m.role}
                    onValueChange={(v) => handleRoleChange(m.user_id, v as WorkspaceRole)}
                    disabled={updateRole.isPending}
                  >
                    <SelectTrigger className="h-7 w-24 text-[11px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROLE_OPTIONS.map((r) => (
                        <SelectItem
                          key={r}
                          value={r}
                          disabled={r === "owner" && myRole !== "owner"}
                        >
                          {r}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <Badge variant="outline" className="text-[10px]">
                    {m.role}
                  </Badge>
                )}
                {canManage && (
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => handleRemove(m.user_id)}
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
      </SettingsCard>
    </SettingsStack>
  );
}

/* ─── Add member (from org) ─────────────────────────────────────── */

/**
 * Picker that adds an *existing org member* to this workspace.
 * Workspace admins assign rather than invite — net-new platform
 * users come in through /org/members, then become assignable here.
 */
function AddMemberCard({ workspaceId }: { workspaceId: string }) {
  const { data: addable, isLoading } = useAddableWorkspaceMembers(workspaceId);
  const addMember = useAddWorkspaceMember(workspaceId);
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("editor");

  const handleAdd = async () => {
    if (!userId) return;
    try {
      await addMember.mutateAsync({ user_id: userId, role });
      toast.success("Member added");
      setUserId("");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  // Hide the card entirely once every org member is in — nothing
  // useful to render and the "no candidates" empty state would just
  // confuse a small team.
  if (!isLoading && (addable ?? []).length === 0) return null;

  return (
    <SettingsCard
      title="Add member"
      description={
        <>
          Pick from members of <strong>this org</strong>. To bring in
          someone new to the platform, invite them at{" "}
          <Link href="/org/members" className="text-primary underline">
            /org/members
          </Link>{" "}
          first.
        </>
      }
    >
      <div className="flex flex-wrap items-end gap-2 p-5">
        <div className="min-w-[220px] flex-1 space-y-1">
          <Label className="text-[11px]">User</Label>
          <Select value={userId} onValueChange={setUserId} disabled={isLoading}>
            <SelectTrigger className="h-9">
              <SelectValue
                placeholder={
                  isLoading ? "Loading…" : "Pick an org member to add"
                }
              />
            </SelectTrigger>
            <SelectContent>
              {(addable ?? []).map((m) => (
                <SelectItem key={m.user_id} value={m.user_id}>
                  <span className="flex flex-col items-start text-xs">
                    <span>{m.full_name || m.email}</span>
                    {m.full_name && (
                      <span className="text-[10px] text-muted-foreground">
                        {m.email}
                      </span>
                    )}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-[11px]">Role</Label>
          <Select
            value={role}
            onValueChange={(v) => setRole(v as WorkspaceRole)}
          >
            <SelectTrigger className="h-9 w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ADD_ROLE_OPTIONS.map((r) => (
                <SelectItem key={r} value={r}>
                  {r}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          size="sm"
          onClick={handleAdd}
          disabled={addMember.isPending || !userId}
        >
          {addMember.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <>
              <Plus className="mr-1 h-3.5 w-3.5" />
              Add
            </>
          )}
        </Button>
      </div>
    </SettingsCard>
  );
}

/* ─── General ───────────────────────────────────────────────────── */

function GeneralPanel({ workspaceId, name }: { workspaceId: string; name: string }) {
  const update = useUpdateWorkspace(workspaceId);
  const [draft, setDraft] = useState(name);
  const dirty = draft.trim() && draft !== name;

  const handleSave = async () => {
    try {
      await update.mutateAsync({ name: draft.trim() });
      toast.success("Workspace updated");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  return (
    <SettingsStack>
      <SettingsCard
        title="General"
        description="Rename workspace. Slug giữ nguyên — đổi slug có thể phá các URL đã share."
      >
        <div className="space-y-3 p-5">
          <div className="space-y-1">
            <Label htmlFor="ws-rename" className="text-[11px]">
              Name
            </Label>
            <Input
              id="ws-rename"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              maxLength={255}
            />
          </div>
          <Button
            size="sm"
            disabled={!dirty || update.isPending}
            onClick={handleSave}
          >
            {update.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              "Save"
            )}
          </Button>
        </div>
      </SettingsCard>
    </SettingsStack>
  );
}

/* ─── Quota cap ─────────────────────────────────────────────────── */

/**
 * Per-workspace quota cap is set in the Org settings now
 * (/org/workspaces). This panel shows the *current* cap read-only,
 * with a link out — workspace admins shouldn't be able to lift their
 * own cap (defeats the cap's purpose).
 */
function QuotaPanel({ workspace }: { workspace: WorkspaceSummaryProp }) {
  return (
    <SettingsStack>
      <SettingsCard
        title="Workspace quota cap"
        description="Read-only. Caps are set by org-admins in Org settings so workspace admins can't lift their own cap."
      >
        <div className="space-y-4 p-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <CapDisplay
              label="Token cap / period"
              value={workspace.monthly_token_quota_override}
            />
            <CapDisplay
              label="KB query cap / period"
              value={workspace.monthly_kb_query_quota_override}
            />
          </div>
          <div className="flex items-center justify-between border-t border-border pt-3">
            <p className="text-[10px] text-muted-foreground">
              Caps don't affect billing — the org still pays for whatever the
              pool draws.
            </p>
            <Button asChild size="sm" variant="outline">
              <Link href="/org/workspaces">Edit in Org →</Link>
            </Button>
          </div>
        </div>
      </SettingsCard>
    </SettingsStack>
  );
}

function CapDisplay({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 font-mono text-sm">
        {value === null ? (
          <span className="text-muted-foreground">No cap</span>
        ) : (
          value.toLocaleString()
        )}
      </div>
    </div>
  );
}

// Re-declare the workspace shape locally so the component file stays
// independent of an exported type — types/index.ts owns the canonical
// definition but the alias keeps the prop signature readable inline.
type WorkspaceSummaryProp = ReturnType<typeof useWorkspaces>["data"] extends
  | Array<infer T>
  | undefined
  ? T
  : never;

/* ─── Danger zone ───────────────────────────────────────────────── */

function DangerZonePanel({
  workspaceId,
  name,
}: {
  workspaceId: string;
  name: string;
}) {
  const router = useRouter();
  const del = useDeleteWorkspace();
  const [confirmText, setConfirmText] = useState("");

  const canDelete = confirmText === name;

  const handleDelete = async () => {
    if (!canDelete) return;
    try {
      await del.mutateAsync(workspaceId);
      toast.success("Workspace deleted");
      // The just-deleted workspace's cookie is now pointing at nothing —
      // bounce to /org so the user picks another (or sees the empty state).
      router.push("/org");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  return (
    <SettingsStack>
      <SettingsCard
        className={cn("border-destructive/40 bg-destructive/5")}
        title="Delete workspace"
        description="Xóa workspace + toàn bộ resources gắn vào (agents, conversations, …). Không reversible."
      >
        <div className="space-y-3 p-5">
          <div className="space-y-1">
            <Label htmlFor="ws-confirm" className="text-[11px]">
              Type the workspace name to confirm: <code className="rounded bg-muted px-1">{name}</code>
            </Label>
            <Input
              id="ws-confirm"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={name}
            />
          </div>
          <Button
            size="sm"
            variant="destructive"
            onClick={handleDelete}
            disabled={!canDelete || del.isPending}
          >
            {del.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              "Delete workspace"
            )}
          </Button>
        </div>
      </SettingsCard>
    </SettingsStack>
  );
}

/* ─── Helpers ───────────────────────────────────────────────────── */

function SkeletonRows() {
  return (
    <div className="space-y-2 p-5">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="h-7 animate-pulse rounded-md bg-muted/60"
        />
      ))}
    </div>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="p-8 text-center text-xs text-muted-foreground">{children}</div>
  );
}

function extractMsg(e: unknown): string {
  if (e && typeof e === "object" && "response" in e) {
    const r = (e as { response?: { data?: { detail?: string } } }).response;
    if (r?.data?.detail) return r.data.detail;
  }
  return e instanceof Error ? e.message : "Something went wrong";
}
