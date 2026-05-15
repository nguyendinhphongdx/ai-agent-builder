"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Building2,
  Check,
  ChevronsUpDown,
  CreditCard,
  Layers,
  Loader2,
  Plus,
  ShieldCheck,
  Users,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  organizationsService,
  type OrganizationSummary,
} from "@/lib/api/organizationsService";
import {
  setActiveOrgId,
  useActiveOrgId,
} from "@/features/organizations/hooks/useActiveOrgId";
import { cn } from "@/lib/utils";

/**
 * Org shell — org-level surface (path: /org/*). Sidebar lists the
 * org-scoped tabs (Workspaces, Members, Billing, Security, Audit,
 * Settings); top holds the brand + org switcher when the user
 * belongs to many orgs.
 *
 * Distinct from the workspace dashboard layout: no workspace
 * switcher here (you're *above* a workspace), no per-workspace
 * resources (agents, chat, …).
 *
 * Active-org state lives in localStorage (see ``useActiveOrgId``),
 * not in the JWT — a user can belong to N orgs and the choice is a
 * pure client preference. The axios client sends the persisted id
 * as ``X-Organization-Id`` on every request so the BE resolves the
 * right org without a separate round-trip.
 *
 * Naming: the existing /hub path belongs to the *marketplace* (paid
 * template store). This page is the *organization* landing — hence
 * /org and not /hub.
 */

const NAV: Array<{ href: string; label: string; icon: React.ElementType }> = [
  { href: "/org/workspaces", label: "Workspaces", icon: Layers },
  { href: "/org/members", label: "Members", icon: Users },
  { href: "/org/billing", label: "Billing", icon: CreditCard },
  { href: "/org/security", label: "Security", icon: ShieldCheck },
  { href: "/org/settings", label: "Settings", icon: Building2 },
];

export function OrgLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const orgsQ = useQuery({
    queryKey: ["organizations"],
    queryFn: () => organizationsService.list(),
    staleTime: 60_000,
  });
  const orgs = orgsQ.data ?? [];
  const activeOrg = useResolvedActiveOrg(orgs);

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-background text-foreground">
      <aside className="flex w-60 shrink-0 flex-col border-r border-border bg-muted/20">
        <div className="border-b border-border px-5 py-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Bot className="h-4 w-4" />
            </div>
            <span className="text-sm font-bold tracking-tight">AgentForge</span>
          </Link>
          <p className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Organization
          </p>
          <OrgSwitcherTrigger
            orgs={orgs}
            activeOrg={activeOrg}
            loading={orgsQ.isLoading}
          />
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] transition-colors",
                  active
                    ? "bg-accent font-medium text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-border p-3 text-[11px] text-muted-foreground">
          <Link
            href="/home"
            className="block rounded-md px-2 py-1.5 transition-colors hover:bg-accent hover:text-foreground"
          >
            ← Back to workspace
          </Link>
          <Link
            href="/hub"
            className="mt-1 block rounded-md px-2 py-1.5 transition-colors hover:bg-accent hover:text-foreground"
          >
            Browse marketplace →
          </Link>
        </div>
      </aside>

      <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}

/* ─── Switcher (inline in sidebar header) ──────────────────────── */

function OrgSwitcherTrigger({
  orgs,
  activeOrg,
  loading,
}: {
  orgs: OrganizationSummary[];
  activeOrg: OrganizationSummary | null;
  loading: boolean;
}) {
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);

  if (loading) {
    return <p className="mt-0.5 truncate text-sm font-medium">…</p>;
  }

  if (!activeOrg) {
    return (
      <>
        <p className="mt-0.5 truncate text-sm font-medium text-muted-foreground">
          No organization
        </p>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="mt-2 inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-wider text-primary hover:underline"
        >
          <Plus className="h-3 w-3" />
          Create org
        </button>
        <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} />
      </>
    );
  }

  // Single-org users get the original static block — no chevron, no
  // dropdown, no localStorage churn.
  if (orgs.length <= 1) {
    return (
      <>
        <p className="mt-0.5 truncate text-sm font-medium">{activeOrg.name}</p>
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
          {activeOrg.plan} · {activeOrg.role}
        </p>
      </>
    );
  }

  const handleSelect = (orgId: string) => {
    if (orgId === activeOrg.id) return;
    setActiveOrgId(orgId);
    // Org context drives nearly every cached query (billing, members,
    // workspaces, security, settings). Wipe the cache so the next
    // fetch goes out with the new X-Organization-Id header.
    qc.invalidateQueries();
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="-mx-1 mt-1 flex w-[calc(100%+0.5rem)] items-center gap-2 rounded-md px-1 py-1 text-left transition-colors hover:bg-accent/50"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{activeOrg.name}</p>
              <p className="truncate text-[10px] uppercase tracking-wider text-muted-foreground">
                {activeOrg.plan} · {activeOrg.role}
              </p>
            </div>
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Switch organization
          </DropdownMenuLabel>
          {orgs.map((o) => (
            <DropdownMenuItem
              key={o.id}
              onClick={() => handleSelect(o.id)}
              className="flex items-start gap-2 py-2"
            >
              <Building2
                className={cn(
                  "mt-0.5 h-3.5 w-3.5 shrink-0",
                  o.id === activeOrg.id
                    ? "text-primary"
                    : "text-muted-foreground",
                )}
              />
              <div className="min-w-0 flex-1">
                <div className="truncate text-xs font-medium">{o.name}</div>
                <div className="truncate text-[10px] uppercase tracking-wider text-muted-foreground">
                  {o.plan} · {o.role}
                </div>
              </div>
              {o.id === activeOrg.id && (
                <Check className="mt-1 h-3 w-3 shrink-0 text-primary" />
              )}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            Create organization
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}

/* ─── Create org dialog ────────────────────────────────────────── */

const SLUG_RE = /^[a-z0-9][a-z0-9-]*[a-z0-9]$/;

function CreateOrgDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);

  // Auto-derive slug while the user hasn't manually edited it.
  const derivedSlug = useMemo(
    () =>
      name
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9-]+/g, "-")
        .replace(/^-+|-+$/g, ""),
    [name],
  );
  const effectiveSlug = slugTouched ? slug : derivedSlug;

  const create = useMutation({
    mutationFn: () =>
      organizationsService.create({
        name: name.trim(),
        slug: effectiveSlug,
      }),
    onSuccess: (org) => {
      toast.success(`Organization "${org.name}" created`);
      setActiveOrgId(org.id);
      qc.invalidateQueries();
      onOpenChange(false);
      setName("");
      setSlug("");
      setSlugTouched(false);
    },
    onError: (e) => toast.error(extractMsg(e)),
  });

  const slugValid = effectiveSlug.length >= 2 && SLUG_RE.test(effectiveSlug);
  const canSubmit = name.trim().length > 0 && slugValid && !create.isPending;

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="w-full max-w-md rounded-lg border border-border bg-card p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold">New organization</h2>
        <p className="mt-1 text-[11px] text-muted-foreground">
          Tạo org mới — bạn tự động là owner. Slug dùng trong URL và link SSO,
          chọn cẩn thận vì không đổi được sau khi tạo.
        </p>
        <div className="mt-4 space-y-3">
          <div className="space-y-1">
            <Label htmlFor="org-create-name" className="text-[11px]">
              Name
            </Label>
            <Input
              id="org-create-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Corp"
              autoFocus
              maxLength={255}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="org-create-slug" className="text-[11px]">
              Slug
            </Label>
            <Input
              id="org-create-slug"
              value={effectiveSlug}
              onChange={(e) => {
                setSlug(e.target.value);
                setSlugTouched(true);
              }}
              placeholder="acme-corp"
              maxLength={64}
            />
            {effectiveSlug && !slugValid && (
              <p className="text-[10px] text-destructive">
                Lowercase letters, digits, dashes — must start + end with a
                letter/digit.
              </p>
            )}
          </div>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={create.isPending}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            disabled={!canSubmit}
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
  );
}

/* ─── Hooks ────────────────────────────────────────────────────── */

/** Resolve the chosen active org from the orgs list + localStorage
 *  preference, falling back to ``orgs[0]`` so single-org users (and
 *  first-time visitors) get a sensible default. */
function useResolvedActiveOrg(
  orgs: OrganizationSummary[],
): OrganizationSummary | null {
  const activeId = useActiveOrgId();
  return useMemo(() => {
    if (orgs.length === 0) return null;
    if (activeId) {
      const match = orgs.find((o) => o.id === activeId);
      if (match) return match;
    }
    return orgs[0];
  }, [orgs, activeId]);
}

/** Hook used by Hub pages so each can get the active org id without
 *  drilling props through the layout. Honours the user's localStorage
 *  selection from the org switcher, with a sane fallback to the first
 *  org the user belongs to. */
export function useActiveOrg() {
  const orgsQ = useQuery({
    queryKey: ["organizations"],
    queryFn: () => organizationsService.list(),
    staleTime: 60_000,
  });
  const orgs = orgsQ.data ?? [];
  const org = useResolvedActiveOrg(orgs);
  return {
    org,
    isLoading: orgsQ.isLoading,
    orgs,
  };
}

/* ─── Helpers ──────────────────────────────────────────────────── */

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
