"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Loader2, Plus, Search, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import {
  systemService,
  type SystemOrgCreateInput,
  type SystemOrgRow,
} from "@/lib/api/systemService";
import { useSystemAccess } from "../hooks/useSystemAccess";

/** Page body for ``/system/organizations``. List + search + create. */
export function OrganizationsView() {
  const { canWrite } = useSystemAccess();
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const q = useQuery({
    queryKey: ["system", "organizations", search],
    queryFn: () => systemService.listOrganizations({ search: search || undefined }),
    staleTime: 10_000,
  });
  const rows = q.data?.rows ?? [];
  const total = q.data?.total ?? 0;

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Organizations</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Every org on the platform. Includes your own system org —
            don&apos;t delete it.
          </p>
        </div>
        {canWrite && (
          <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            New organization
          </Button>
        )}
      </header>

      <div className="mt-6 flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or slug…"
            className="h-8 pl-8 text-xs"
          />
        </div>
        <p className="text-[11px] text-muted-foreground">
          {q.isLoading ? "…" : `${total} org${total === 1 ? "" : "s"}`}
        </p>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-border">
        {q.isLoading ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
          </div>
        ) : rows.length === 0 ? (
          <p className="px-4 py-12 text-center text-xs text-muted-foreground">
            No organizations match.
          </p>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-muted/40 text-[10px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="px-4 py-2 text-left font-semibold">Name</th>
                <th className="px-4 py-2 text-left font-semibold">Slug</th>
                <th className="px-4 py-2 text-left font-semibold">Plan</th>
                <th className="px-4 py-2 text-right font-semibold">Members</th>
                <th className="px-4 py-2 text-right font-semibold">Workspaces</th>
                <th className="px-4 py-2 text-left font-semibold">Created</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <OrgRow key={r.id} row={r} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {createOpen && (
        <CreateOrgDialog
          open={createOpen}
          onClose={() => setCreateOpen(false)}
        />
      )}
    </div>
  );
}

function OrgRow({ row }: { row: SystemOrgRow }) {
  return (
    <tr className="border-t border-border transition-colors hover:bg-muted/30">
      <td className="px-4 py-2">
        <div className="flex items-center gap-2">
          {row.is_system ? (
            <ShieldCheck className="h-3.5 w-3.5 text-primary" />
          ) : (
            <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
          )}
          <span className="font-medium text-foreground">{row.name}</span>
          {row.is_system && (
            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wider text-primary">
              System
            </span>
          )}
        </div>
      </td>
      <td className="px-4 py-2 font-mono text-[11px] text-muted-foreground">{row.slug}</td>
      <td className="px-4 py-2">
        <span
          className={cn(
            "inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider",
            row.plan === "enterprise"
              ? "bg-violet-500/10 text-violet-600 dark:text-violet-400"
              : row.plan === "pro"
                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                : row.plan === "starter"
                  ? "bg-sky-500/10 text-sky-600 dark:text-sky-400"
                  : "bg-muted text-muted-foreground",
          )}
        >
          {row.plan}
        </span>
      </td>
      <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">
        {row.member_count}
      </td>
      <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">
        {row.workspace_count}
      </td>
      <td className="px-4 py-2 text-[11px] text-muted-foreground">
        {new Date(row.created_at).toLocaleDateString()}
      </td>
    </tr>
  );
}

const SLUG_RE = /^[a-z0-9][a-z0-9-]*[a-z0-9]$/;

function CreateOrgDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [form, setForm] = useState<SystemOrgCreateInput>({
    name: "",
    slug: "",
    owner_email: "",
    plan: "free",
  });

  const create = useMutation({
    mutationFn: () => systemService.createOrganization(form),
    onSuccess: (org) => {
      toast.success(`Created "${org.name}"`);
      qc.invalidateQueries({ queryKey: ["system", "organizations"] });
      onClose();
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  if (!open) return null;
  const slugValid = form.slug.length >= 2 && SLUG_RE.test(form.slug);
  const canSubmit =
    form.name.trim().length > 0 &&
    slugValid &&
    form.owner_email.includes("@") &&
    !create.isPending;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-lg border border-border bg-card p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold">New organization</h2>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Mint an org on a customer&apos;s behalf. Owner email must already
          exist as a user on the platform.
        </p>

        <div className="mt-4 space-y-3">
          <div className="space-y-1">
            <Label htmlFor="sys-name" className="text-[11px]">Name</Label>
            <Input
              id="sys-name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              autoFocus
              maxLength={255}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sys-slug" className="text-[11px]">Slug</Label>
            <Input
              id="sys-slug"
              value={form.slug}
              onChange={(e) =>
                setForm({ ...form, slug: e.target.value.toLowerCase() })
              }
              placeholder="acme-corp"
              maxLength={64}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sys-owner" className="text-[11px]">
              Owner email
            </Label>
            <Input
              id="sys-owner"
              type="email"
              value={form.owner_email}
              onChange={(e) =>
                setForm({ ...form, owner_email: e.target.value })
              }
              placeholder="owner@example.com"
            />
            <p className="text-[10px] text-muted-foreground">
              Must already exist as a registered user.
            </p>
          </div>
          <div className="space-y-1">
            <Label htmlFor="sys-plan" className="text-[11px]">Plan</Label>
            <select
              id="sys-plan"
              value={form.plan ?? "free"}
              onChange={(e) => setForm({ ...form, plan: e.target.value })}
              className="block w-full rounded-md border border-border bg-background px-3 py-1.5 text-xs"
            >
              <option value="free">Free</option>
              <option value="starter">Starter</option>
              <option value="pro">Pro</option>
              <option value="enterprise">Enterprise</option>
            </select>
          </div>
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={create.isPending}>
            Cancel
          </Button>
          <Button size="sm" disabled={!canSubmit} onClick={() => create.mutate()}>
            {create.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Create"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function extractMsg(err: unknown): string {
  const anyErr = err as { response?: { data?: { detail?: unknown } }; message?: string };
  const d = anyErr?.response?.data?.detail;
  if (typeof d === "string") {
    // Map common BE codes to friendly copy.
    const map: Record<string, string> = {
      slug_taken: "That slug is already used.",
      slug_reserved: "That slug is reserved for platform internals.",
      owner_not_found: "No user found for that email.",
    };
    return map[d] ?? d;
  }
  return anyErr?.message ?? "Request failed";
}
