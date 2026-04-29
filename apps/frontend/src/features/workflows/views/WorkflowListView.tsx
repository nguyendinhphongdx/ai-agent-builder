"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus, GitBranch, MoreHorizontal, Trash2, Search, Play,
  CheckCircle2, XCircle, Clock, Copy, Download, Zap,
} from "lucide-react";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useWorkflows, useCreateWorkflow, useDeleteWorkflow, useWorkflowRuns,
} from "../hooks/useWorkflows";
import type { Workflow } from "../types";
import { cn } from "@/lib/utils";

const STATUS_FILTERS = ["all", "active", "draft"] as const;

function timeAgo(date: string) {
  const diff = Date.now() - new Date(date).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function WorkflowListView() {
  const router = useRouter();
  const { data: workflows, isLoading } = useWorkflows();
  const createWorkflow = useCreateWorkflow();
  const deleteWorkflow = useDeleteWorkflow();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    if (!workflows) return [];
    return workflows.filter((wf) => {
      const matchSearch = !search || wf.name.toLowerCase().includes(search.toLowerCase());
      const matchStatus = statusFilter === "all"
        || (statusFilter === "active" && wf.is_active)
        || (statusFilter === "draft" && !wf.is_active);
      return matchSearch && matchStatus;
    });
  }, [workflows, search, statusFilter]);

  // Aggregate stats
  const stats = useMemo(() => {
    if (!workflows) return { total: 0, active: 0, draft: 0 };
    return {
      total: workflows.length,
      active: workflows.filter((w) => w.is_active).length,
      draft: workflows.filter((w) => !w.is_active).length,
    };
  }, [workflows]);

  const handleCreate = () => {
    createWorkflow.mutate({ name: `Workflow ${(workflows?.length ?? 0) + 1}` });
  };

  const handleDuplicate = (wf: Workflow) => {
    createWorkflow.mutate({ name: `${wf.name} (copy)`, description: wf.description ?? undefined });
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="mb-6 h-8 w-48 animate-pulse rounded-lg bg-muted" />
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[1, 2, 3].map((i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />)}
        </div>
        <div className="space-y-2">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-linear-to-b from-background to-muted/20">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/70 bg-background/80 px-6 py-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">Workflows</h1>
          <span className="text-xs text-muted-foreground">{stats.total} total</span>
        </div>
        <Button onClick={handleCreate} disabled={createWorkflow.isPending} size="sm" className="gap-1.5">
          <Plus className="h-3.5 w-3.5" />
          New Workflow
        </Button>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search workflows..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="h-8 pl-8 text-sm"
            />
          </div>
          <div className="flex items-center gap-1 rounded-lg border border-border bg-muted/50 p-0.5">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  "rounded-md px-2.5 py-1 text-[11px] font-medium capitalize transition-colors",
                  statusFilter === s
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {s}
              </button>
            ))}
          </div>

          {stats.total > 0 && (
            <div className="ml-auto flex items-center gap-4 text-xs text-muted-foreground">
              <span>{stats.total} total</span>
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                {stats.active} active
              </span>
              <span>{stats.draft} draft</span>
            </div>
          )}
        </div>

        {/* Workflow list */}
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-violet-200 bg-violet-50 dark:border-violet-500/20 dark:bg-violet-500/10">
              <GitBranch className="h-7 w-7 text-violet-500" />
            </div>
            <p className="text-base font-medium">
              {search ? "No workflows match your search" : "No workflows yet"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {search ? "Try a different search term" : "Create your first workflow to automate agent tasks"}
            </p>
            {!search && (
              <div className="mt-5 flex gap-3">
                <Button onClick={handleCreate} size="sm" className="gap-1.5">
                  <Plus className="h-3.5 w-3.5" />
                  Create Workflow
                </Button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((wf) => (
              <WorkflowRow
                key={wf.id}
                workflow={wf}
                onDelete={() => deleteWorkflow.mutate(wf.id)}
                onDuplicate={() => handleDuplicate(wf)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function WorkflowRow({
  workflow: wf,
  onDelete,
  onDuplicate,
}: {
  workflow: Workflow;
  onDelete: () => void;
  onDuplicate: () => void;
}) {
  // N+1 by design until the list endpoint includes `last_run` — keyed off
  // the shared runs cache so any execute() invalidation flows here.
  const { data: runs } = useWorkflowRuns(wf.id, 1);
  const lastRun = runs?.[0];

  return (
    <Link
      href={`/workflows/${wf.id}`}
      className="group flex items-center gap-4 rounded-xl border border-border bg-card p-4 transition-all hover:shadow-sm hover:border-violet-200 dark:hover:border-violet-500/30"
    >
      {/* Icon */}
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-violet-100 dark:bg-violet-500/15">
        <GitBranch className="h-5 w-5 text-violet-600 dark:text-violet-400" />
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold truncate">{wf.name}</h3>
          <Badge
            variant="secondary"
            className={cn(
              "text-[10px] px-1.5 h-5 shrink-0",
              wf.is_active
                ? "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-300 dark:border-emerald-500/30"
                : "bg-muted text-muted-foreground"
            )}
          >
            {wf.is_active ? "Active" : "Draft"}
          </Badge>
          <span className="text-[10px] text-muted-foreground">v{wf.version}</span>
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground truncate">
          {wf.description || "No description"}
        </p>
      </div>

      {/* Last run status */}
      {lastRun && (
        <div className="flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 text-xs">
            {lastRun.status === "completed" ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
            ) : lastRun.status === "failed" ? (
              <XCircle className="h-3.5 w-3.5 text-red-500" />
            ) : (
              <Clock className="h-3.5 w-3.5 text-amber-500 animate-spin" />
            )}
            <span className="text-muted-foreground">{timeAgo(lastRun.started_at)}</span>
          </div>
          {lastRun.total_tokens > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <Zap className="h-2.5 w-2.5" />{lastRun.total_tokens}
            </span>
          )}
        </div>
      )}

      {/* Quick actions */}
      <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="outline"
          size="icon-xs"
          className="h-7 w-7"
          onClick={(e) => {
            e.preventDefault();
            // TODO: quick run
          }}
          title="Run"
        >
          <Play className="h-3 w-3" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon-xs" className="h-7 w-7" onClick={(e) => e.preventDefault()}>
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onClick={(e) => { e.preventDefault(); onDuplicate(); }}>
              <Copy className="mr-2 h-3.5 w-3.5" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuItem onClick={(e) => { e.preventDefault(); }}>
              <Download className="mr-2 h-3.5 w-3.5" />
              Export JSON
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => { e.preventDefault(); onDelete(); }}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-3.5 w-3.5" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </Link>
  );
}
