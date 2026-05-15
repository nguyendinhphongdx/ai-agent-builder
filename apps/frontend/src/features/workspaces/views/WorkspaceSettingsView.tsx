"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  SettingsCard,
  SettingsPageHeader,
  SettingsStack,
} from "@/features/settings/components/SettingsPrimitives";
import { useQuery } from "@tanstack/react-query";
import { billingService } from "@/lib/api/billingService";
import {
  useWorkspaces,
  useUpdateWorkspace,
  useDeleteWorkspace,
  useWorkspaceMembers,
  useUpdateMemberRole,
  useRemoveMember,
  useWorkspaceInvitations,
  useCreateInvitation,
  useRevokeInvitation,
} from "../hooks/useWorkspaces";
import { RoleInspector } from "../components/RoleInspector";
import { useWorkspaceStore } from "../stores/workspaceStore";
import { roleAtLeast, type WorkspaceRole } from "../types";

const ROLE_OPTIONS: WorkspaceRole[] = ["viewer", "editor", "admin", "owner"];
const INVITE_ROLE_OPTIONS: WorkspaceRole[] = ["viewer", "editor", "admin"];

export function WorkspaceSettingsView() {
  const router = useRouter();
  const { data: workspaces } = useWorkspaces();
  const currentId = useWorkspaceStore((s) => s.currentWorkspaceId);
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
          {canManage && <TabsTrigger value="invitations">Invitations</TabsTrigger>}
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

        {canManage && (
          <TabsContent value="invitations" className="mt-4">
            <InvitationsPanel workspaceId={current.id} />
          </TabsContent>
        )}

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
                  <select
                    value={m.role}
                    onChange={(e) =>
                      handleRoleChange(m.user_id, e.target.value as WorkspaceRole)
                    }
                    disabled={updateRole.isPending}
                    className="h-7 rounded-md border border-border bg-background px-2 text-[11px]"
                  >
                    {ROLE_OPTIONS.map((r) => (
                      <option
                        key={r}
                        value={r}
                        disabled={r === "owner" && myRole !== "owner"}
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

/* ─── Invitations ───────────────────────────────────────────────── */

function InvitationsPanel({ workspaceId }: { workspaceId: string }) {
  const { data: invites, isLoading } = useWorkspaceInvitations(workspaceId);
  const create = useCreateInvitation(workspaceId);
  const revoke = useRevokeInvitation(workspaceId);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<WorkspaceRole>("editor");

  const handleInvite = async () => {
    const trimmed = email.trim();
    if (!trimmed) return;
    try {
      const inv = await create.mutateAsync({ email: trimmed, role });
      toast.success(`Invited ${trimmed}`);
      // Copy the accept URL to clipboard so the admin can paste it
      // into Slack/email immediately — no mail delivery dependency.
      const url = `${window.location.origin}/workspaces/invitations/${inv.token}`;
      await navigator.clipboard.writeText(url).catch(() => undefined);
      setEmail("");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  const handleRevoke = async (invId: string) => {
    if (!confirm("Revoke this invitation?")) return;
    try {
      await revoke.mutateAsync(invId);
      toast.success("Invitation revoked");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  return (
    <SettingsStack>
      <SettingsCard
        title="Send invitation"
        description="Token URL được copy vào clipboard sau khi tạo. Paste cho người được mời."
      >
        <div className="flex flex-wrap items-end gap-2 p-5">
          <div className="flex-1 space-y-1 min-w-[200px]">
            <Label htmlFor="invite-email" className="text-[11px]">
              Email
            </Label>
            <Input
              id="invite-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="teammate@example.com"
              className="h-9"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="invite-role" className="text-[11px]">
              Role
            </Label>
            <select
              id="invite-role"
              value={role}
              onChange={(e) => setRole(e.target.value as WorkspaceRole)}
              className="h-9 rounded-md border border-border bg-background px-2 text-xs"
            >
              {INVITE_ROLE_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <Button
            size="sm"
            onClick={handleInvite}
            disabled={create.isPending || !email.trim()}
          >
            {create.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <>
                <Plus className="mr-1 h-3.5 w-3.5" />
                Invite
              </>
            )}
          </Button>
        </div>
      </SettingsCard>

      <SettingsCard title="Pending invitations">
        {isLoading ? (
          <SkeletonRows />
        ) : !invites || invites.length === 0 ? (
          <Empty>Chưa có invitation đang chờ.</Empty>
        ) : (
          <ul className="divide-y divide-border">
            {invites.map((inv) => (
              <li
                key={inv.id}
                className="flex items-center gap-3 px-5 py-3 text-xs"
              >
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{inv.email}</div>
                  <div className="text-[10px] text-muted-foreground">
                    {inv.role} · expires{" "}
                    {new Date(inv.expires_at).toLocaleDateString()}
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-[11px]"
                  onClick={() => {
                    const url = `${window.location.origin}/workspaces/invitations/${inv.token}`;
                    navigator.clipboard.writeText(url);
                    toast.success("Copied invite URL");
                  }}
                >
                  Copy URL
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => handleRevoke(inv.id)}
                  disabled={revoke.isPending}
                  className="text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </SettingsCard>
    </SettingsStack>
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
 * Per-workspace soft cap on top of the org's plan quota. NULL = no
 * cap, share the org pool freely. Positive int = hard block once this
 * workspace consumes that much in the current billing period.
 *
 * Caps don't affect billing — the org still pays for whatever the
 * pool draws. They exist to prevent waste (a runaway sandbox agent
 * draining the production pool).
 */
function QuotaPanel({ workspace }: { workspace: WorkspaceSummaryProp }) {
  const update = useUpdateWorkspace(workspace.id);
  const billingQ = useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: () => billingService.getSubscription(),
    staleTime: 60_000,
  });

  // Local "draft" form state — initialise from the workspace record
  // and let the user edit before saving. Strings (not numbers) so the
  // input can be cleared without flipping to 0.
  const [tokenDraft, setTokenDraft] = useState(
    workspace.monthly_token_quota_override?.toString() ?? "",
  );
  const [kbDraft, setKbDraft] = useState(
    workspace.monthly_kb_query_quota_override?.toString() ?? "",
  );

  const tokenDraftN = tokenDraft.trim() === "" ? null : Number(tokenDraft);
  const kbDraftN = kbDraft.trim() === "" ? null : Number(kbDraft);

  const tokenDirty = tokenDraftN !== workspace.monthly_token_quota_override;
  const kbDirty = kbDraftN !== workspace.monthly_kb_query_quota_override;
  const dirty = tokenDirty || kbDirty;
  const invalid =
    (tokenDraftN !== null && (!Number.isFinite(tokenDraftN) || tokenDraftN < 0)) ||
    (kbDraftN !== null && (!Number.isFinite(kbDraftN) || kbDraftN < 0));

  const handleSave = async () => {
    if (invalid) return;
    try {
      await update.mutateAsync({
        monthly_token_quota_override: tokenDraftN,
        monthly_kb_query_quota_override: kbDraftN,
      });
      toast.success("Quota cap updated");
    } catch (e) {
      toast.error(extractMsg(e));
    }
  };

  const orgPlan = billingQ.data?.subscription.plan;
  const orgTokens = billingQ.data?.tokens;
  const orgKb = billingQ.data?.kb_queries;

  return (
    <SettingsStack>
      <SettingsCard
        title="Workspace quota cap"
        description={
          orgPlan
            ? `Org "${workspace.organization.name}" đang ở plan ${orgPlan.name}. Cap mềm dưới đây giới hạn workspace này tiêu hết bao nhiêu trong pool chung. Bỏ trống = không cap.`
            : "Cap mềm giới hạn workspace này tiêu bao nhiêu trong pool chung của org. Bỏ trống = không cap."
        }
      >
        <div className="space-y-5 p-5">
          {/* Org-level context — show plan limit + current usage so the
              admin picks a cap that's actually meaningful. */}
          {orgPlan && (
            <div className="rounded-md border border-border bg-muted/30 p-3 text-[11px]">
              <div className="mb-2 font-semibold uppercase tracking-wider text-muted-foreground">
                Org pool (toàn bộ workspaces)
              </div>
              <UsageRow
                label="Tokens"
                used={orgTokens?.used ?? 0}
                limit={orgPlan.monthly_llm_tokens}
              />
              <UsageRow
                label="KB queries"
                used={orgKb?.used ?? 0}
                limit={orgPlan.monthly_kb_queries}
              />
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1">
              <Label htmlFor="ws-token-cap" className="text-[11px]">
                Token cap / billing period
              </Label>
              <Input
                id="ws-token-cap"
                type="number"
                min={0}
                inputMode="numeric"
                value={tokenDraft}
                onChange={(e) => setTokenDraft(e.target.value)}
                placeholder="Không cap"
              />
              <p className="text-[10px] text-muted-foreground">
                {orgPlan
                  ? `Plan ${orgPlan.name} cho phép tối đa ${formatNumber(orgPlan.monthly_llm_tokens)} tokens / period cho toàn org.`
                  : "Bỏ trống = workspace dùng chung pool của org."}
              </p>
            </div>

            <div className="space-y-1">
              <Label htmlFor="ws-kb-cap" className="text-[11px]">
                KB query cap / billing period
              </Label>
              <Input
                id="ws-kb-cap"
                type="number"
                min={0}
                inputMode="numeric"
                value={kbDraft}
                onChange={(e) => setKbDraft(e.target.value)}
                placeholder="Không cap"
              />
              <p className="text-[10px] text-muted-foreground">
                {orgPlan
                  ? `Plan ${orgPlan.name}: tối đa ${formatNumber(orgPlan.monthly_kb_queries)} KB queries.`
                  : "Bỏ trống = workspace dùng chung pool của org."}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-border pt-3">
            <p className="text-[10px] text-muted-foreground">
              Cap mềm chỉ chặn workspace này — không ảnh hưởng billing.
              Org vẫn trả theo plan + metered overage thông thường.
            </p>
            <Button
              size="sm"
              disabled={!dirty || invalid || update.isPending}
              onClick={handleSave}
            >
              {update.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                "Save cap"
              )}
            </Button>
          </div>
        </div>
      </SettingsCard>
    </SettingsStack>
  );
}

function UsageRow({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  // limit=0 sentinel = unlimited (matches plans.py UNLIMITED).
  const isUnlimited = limit === 0;
  const pct = isUnlimited ? 0 : Math.min(100, Math.round((used / Math.max(limit, 1)) * 100));
  return (
    <div className="mb-1.5 last:mb-0">
      <div className="flex justify-between font-mono text-[10px]">
        <span>{label}</span>
        <span className="text-muted-foreground">
          {formatNumber(used)} / {isUnlimited ? "∞" : formatNumber(limit)}
        </span>
      </div>
      {!isUnlimited && (
        <div className="mt-0.5 h-1 overflow-hidden rounded-full bg-muted">
          <div
            className={cn(
              "h-full transition-all",
              pct >= 90 ? "bg-destructive" : pct >= 70 ? "bg-amber-500" : "bg-primary",
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
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
      router.push("/home");
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
