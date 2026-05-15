"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LogIn, Loader2, Lock, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { organizationsService, type OrganizationWorkspaceSummary } from "@/lib/api/organizationsService";
import { workspaceService } from "@/lib/api/workspaceService";
import { sessionService } from "@/lib/api/sessionService";
import { billingService } from "@/lib/api/billingService";
import { useActiveOrg } from "@/features/hub/components/HubLayout";
import { cn } from "@/lib/utils";

/**
 * Hub → Workspaces tab.
 *
 * Shows every workspace under the active org (not just ones the
 * caller is a direct member of — the BE endpoint widens the view
 * for org-admins). Per row:
 *   - Enter button → ``sessionService.enter`` then route to /home
 *   - Quota cap inputs (token + KB) with inline save
 *   - Member count + personal/team badge
 *   - Delete (if non-personal)
 *
 * Plus a "Create workspace" button at the top.
 */
export default function HubWorkspacesPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { org, isLoading: orgLoading } = useActiveOrg();
  const billingQ = useQuery({
    queryKey: ["billing", "subscription"],
    queryFn: () => billingService.getSubscription(),
    staleTime: 60_000,
  });

  const workspacesQ = useQuery({
    queryKey: ["organizations", org?.id, "workspaces"],
    queryFn: () => organizationsService.listWorkspaces(org!.id),
    enabled: !!org,
  });

  const enterM = useMutation({
    mutationFn: (workspace_id: string) => sessionService.enter(workspace_id),
    onSuccess: (data) => {
      toast.success(`Entered ${data.workspace_name}`);
      router.push("/home");
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  if (orgLoading || !org) {
    return <Spinner />;
  }

  const plan = billingQ.data?.subscription.plan;

  return (
    <div className="mx-auto max-w-5xl px-6 py-10 lg:px-8">
      <header className="flex items-start justify-between gap-4 border-b border-border pb-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workspaces</h1>
          <p className="mt-1 max-w-xl text-xs text-muted-foreground">
            Every workspace inside <strong>{org.name}</strong>. Use Enter to
            switch the active session into one; quota caps below set how much
            of the org pool each workspace can consume per billing period.
          </p>
        </div>
        <CreateWorkspaceButton orgId={org.id} onCreated={() =>
          qc.invalidateQueries({ queryKey: ["organizations", org.id, "workspaces"] })
        } />
      </header>

      {plan && (
        <div className="mt-6 rounded-md border border-border bg-muted/30 p-3 text-[11px]">
          <span className="font-semibold uppercase tracking-wider text-muted-foreground">
            Org pool ({plan.name})
          </span>
          <div className="mt-1 font-mono text-[11px]">
            {billingQ.data?.tokens.used.toLocaleString()} /{" "}
            {plan.monthly_llm_tokens === 0
              ? "∞"
              : plan.monthly_llm_tokens.toLocaleString()}{" "}
            tokens · {billingQ.data?.kb_queries.used.toLocaleString()} /{" "}
            {plan.monthly_kb_queries === 0
              ? "∞"
              : plan.monthly_kb_queries.toLocaleString()}{" "}
            KB queries
          </div>
        </div>
      )}

      <section className="mt-6 space-y-3">
        {workspacesQ.isLoading ? (
          <Spinner />
        ) : (workspacesQ.data ?? []).length === 0 ? (
          <Empty>No workspaces in this organization yet.</Empty>
        ) : (
          (workspacesQ.data ?? []).map((ws) => (
            <WorkspaceCard
              key={ws.id}
              workspace={ws}
              onEnter={() => enterM.mutate(ws.id)}
              entering={enterM.isPending && enterM.variables === ws.id}
              orgId={org.id}
            />
          ))
        )}
      </section>
    </div>
  );
}

/* ─── Per-workspace card ────────────────────────────────────────── */

function WorkspaceCard({
  workspace,
  onEnter,
  entering,
  orgId,
}: {
  workspace: OrganizationWorkspaceSummary;
  onEnter: () => void;
  entering: boolean;
  orgId: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate font-medium">{workspace.name}</span>
            {workspace.is_personal && (
              <Badge variant="outline" className="text-[10px]">
                personal
              </Badge>
            )}
            {workspace.force_mfa && (
              <Badge variant="outline" className="text-[10px]">
                <Lock className="mr-1 h-2.5 w-2.5" /> MFA required
              </Badge>
            )}
          </div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">
            {workspace.slug} · {workspace.member_count} member
            {workspace.member_count === 1 ? "" : "s"}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={onEnter}
            disabled={entering}
          >
            {entering ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <LogIn className="mr-1.5 h-3.5 w-3.5" />
            )}
            Enter
          </Button>
          {!workspace.is_personal && <DeleteWorkspaceButton workspace={workspace} orgId={orgId} />}
        </div>
      </div>
      <QuotaCapRow workspace={workspace} orgId={orgId} />
    </div>
  );
}

/* ─── Inline quota cap row ─────────────────────────────────────── */

function QuotaCapRow({
  workspace,
  orgId,
}: {
  workspace: OrganizationWorkspaceSummary;
  orgId: string;
}) {
  const qc = useQueryClient();
  const [tokenDraft, setTokenDraft] = useState(
    workspace.monthly_token_quota_override?.toString() ?? "",
  );
  const [kbDraft, setKbDraft] = useState(
    workspace.monthly_kb_query_quota_override?.toString() ?? "",
  );

  // Re-sync drafts if the workspace row refetches with new server values.
  useEffect(() => {
    setTokenDraft(workspace.monthly_token_quota_override?.toString() ?? "");
    setKbDraft(workspace.monthly_kb_query_quota_override?.toString() ?? "");
  }, [
    workspace.monthly_token_quota_override,
    workspace.monthly_kb_query_quota_override,
  ]);

  const tokenN = tokenDraft.trim() === "" ? null : Number(tokenDraft);
  const kbN = kbDraft.trim() === "" ? null : Number(kbDraft);
  const dirty =
    tokenN !== workspace.monthly_token_quota_override ||
    kbN !== workspace.monthly_kb_query_quota_override;
  const invalid =
    (tokenN !== null && (!Number.isFinite(tokenN) || tokenN < 0)) ||
    (kbN !== null && (!Number.isFinite(kbN) || kbN < 0));

  const save = useMutation({
    mutationFn: () =>
      workspaceService.update(workspace.id, {
        monthly_token_quota_override: tokenN,
        monthly_kb_query_quota_override: kbN,
      }),
    onSuccess: () => {
      toast.success("Quota cap updated");
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "workspaces"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  return (
    <div className="grid gap-3 px-5 py-3 sm:grid-cols-[1fr_1fr_auto]">
      <div className="space-y-1">
        <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Token cap / period
        </Label>
        <Input
          type="number"
          min={0}
          inputMode="numeric"
          placeholder="No cap"
          value={tokenDraft}
          onChange={(e) => setTokenDraft(e.target.value)}
          className="h-8 text-xs"
        />
      </div>
      <div className="space-y-1">
        <Label className="text-[10px] uppercase tracking-wider text-muted-foreground">
          KB query cap / period
        </Label>
        <Input
          type="number"
          min={0}
          inputMode="numeric"
          placeholder="No cap"
          value={kbDraft}
          onChange={(e) => setKbDraft(e.target.value)}
          className="h-8 text-xs"
        />
      </div>
      <div className="flex items-end">
        <Button
          size="sm"
          variant={dirty ? "default" : "ghost"}
          disabled={!dirty || invalid || save.isPending}
          onClick={() => save.mutate()}
        >
          {save.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            "Save"
          )}
        </Button>
      </div>
    </div>
  );
}

/* ─── Create dialog (inline button + dialog) ───────────────────── */

function CreateWorkspaceButton({
  orgId,
  onCreated,
}: {
  orgId: string;
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const create = useMutation({
    mutationFn: () => workspaceService.create({ name, organization_id: orgId }),
    onSuccess: () => {
      toast.success("Workspace created");
      setOpen(false);
      setName("");
      onCreated();
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  return (
    <>
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus className="mr-1.5 h-3.5 w-3.5" />
        New workspace
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
            <h2 className="text-base font-semibold">New workspace</h2>
            <p className="mt-1 text-[11px] text-muted-foreground">
              Tạo workspace mới trong org. Bạn tự động là owner.
            </p>
            <div className="mt-4 space-y-1">
              <Label htmlFor="ws-new-name" className="text-[11px]">
                Name
              </Label>
              <Input
                id="ws-new-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Marketing"
                autoFocus
              />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                size="sm"
                disabled={!name.trim() || create.isPending}
                onClick={() => create.mutate()}
              >
                {create.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  "Create"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/* ─── Delete button ────────────────────────────────────────────── */

function DeleteWorkspaceButton({
  workspace,
  orgId,
}: {
  workspace: OrganizationWorkspaceSummary;
  orgId: string;
}) {
  const qc = useQueryClient();
  const del = useMutation({
    mutationFn: () => workspaceService.delete(workspace.id),
    onSuccess: () => {
      toast.success("Workspace deleted");
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "workspaces"] });
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={() => {
        if (confirm(`Delete ${workspace.name}? This cannot be undone.`)) {
          del.mutate();
        }
      }}
      disabled={del.isPending}
      className="text-muted-foreground hover:text-destructive"
    >
      {del.isPending ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Trash2 className="h-3.5 w-3.5" />
      )}
    </Button>
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
    <div className={cn("rounded-md border border-dashed border-border p-8 text-center text-xs text-muted-foreground")}>
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
