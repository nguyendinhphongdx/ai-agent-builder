"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  Bot,
  MessageSquare,
  LayoutGrid,
  List,
  CalendarDays,
  Globe,
  Lock,
  MoreHorizontal,
  Pencil,
  Share2,
  Trash2,
} from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAgents, useDeleteAgent } from "../hooks/useAgents";
import { useModelCatalog, findProvider, modelDisplayName, providerOfModel } from "@/lib/models/catalog";
import type { AgentListItem } from "../types";
import { cn } from "@/lib/utils";
import { AgentAvatar } from "../components/AgentAvatar";

const STATUS_FILTERS = ["all", "draft", "active", "archived"] as const;

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function AgentLibraryView() {
  const { data: agents, isLoading } = useAgents();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const filtered = useMemo(() => {
    if (!agents) return [];
    return agents.filter((a) => {
      const matchSearch =
        !search ||
        a.name.toLowerCase().includes(search.toLowerCase()) ||
        a.description?.toLowerCase().includes(search.toLowerCase());
      const matchStatus = statusFilter === "all" || a.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [agents, search, statusFilter]);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="mb-6 h-8 w-48 animate-pulse rounded-lg bg-muted" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-xl bg-muted/70" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-linear-to-b flex h-full flex-col from-background via-background to-muted/25">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-border/70 bg-background/80 px-6 py-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">Libraries</h1>
          <span className="text-xs text-muted-foreground">{agents?.length ?? 0} agents</span>
        </div>
        <Link
          href="/agents/new"
          className={cn(buttonVariants({ size: "sm" }), "gap-1.5")}
        >
          <Plus className="h-3.5 w-3.5" />
          New Agent
        </Link>
      </div>

      {/* Filters row */}
      <div className="flex items-center gap-3 border-b border-border/70 bg-background/50 px-6 py-2.5">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 border-border bg-muted/60 pl-8 text-sm placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-primary/30"
          />
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-border/70 bg-muted/50 p-0.5">
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

        <div className="ml-auto flex items-center gap-1 rounded-lg border border-border/70 bg-muted/50 p-0.5">
          <button
            onClick={() => setViewMode("grid")}
            className={cn(
              "rounded-md p-1 transition-colors",
              viewMode === "grid"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={cn(
              "rounded-md p-1 transition-colors",
              viewMode === "list"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <List className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-6">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-primary/20 bg-primary/10">
              <Bot className="h-6 w-6 text-primary" />
            </div>
            <p className="text-sm text-muted-foreground">
              {search ? "No agents match your search" : "No agents yet"}
            </p>
            {!search && (
              <Link
                href="/agents/new"
                className={cn(buttonVariants({ size: "sm" }), "mt-4 gap-1.5")}
              >
                <Plus className="h-3.5 w-3.5" />
                Create your first agent
              </Link>
            )}
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map((agent) => (
              <AgentGridCard key={agent.id} agent={agent} />
            ))}
          </div>
        ) : (
          <div className="space-y-1">
            {filtered.map((agent) => (
              <AgentListRow key={agent.id} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Agent Actions Menu ─────────────────────────────────────── */

function AgentActionsMenu({ agent }: { agent: AgentListItem }) {
  const router = useRouter();
  const deleteAgent = useDeleteAgent();

  const handleDelete = () => {
    if (!confirm(`Xoá agent "${agent.name}"?`)) return;
    deleteAgent.mutate(agent.id);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-md border border-border/70 bg-background/90 text-muted-foreground opacity-0 shadow-sm backdrop-blur transition-all hover:bg-accent hover:text-foreground group-hover:opacity-100"
          onClick={(e) => e.preventDefault()}
        >
          <MoreHorizontal className="h-3.5 w-3.5" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        <DropdownMenuItem
          onClick={(e) => {
            e.preventDefault();
            router.push(`/agents/${agent.id}`);
          }}
        >
          <Pencil className="mr-2 h-3.5 w-3.5" />
          Chỉnh sửa
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={(e) => {
            e.preventDefault();
            navigator.clipboard.writeText(
              `${window.location.origin}/agents/${agent.id}/chat`
            );
          }}
        >
          <Share2 className="mr-2 h-3.5 w-3.5" />
          Chia sẻ link
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={(e) => {
            e.preventDefault();
            handleDelete();
          }}
          className="text-destructive focus:text-destructive"
        >
          <Trash2 className="mr-2 h-3.5 w-3.5" />
          Xoá
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/* ─── Grid Card ──────────────────────────────────────────────── */

function AgentGridCard({ agent }: { agent: AgentListItem }) {
  const { data: catalog } = useModelCatalog();
  return (
    <Link
      href={`/agents/${agent.id}/chat`}
      className="group relative flex min-h-42 flex-col rounded-xl border border-border/70 bg-card/80 p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-md"
    >
      {/* Actions menu - top right */}
      <div className="absolute right-2.5 top-2.5 z-10">
        <AgentActionsMenu agent={agent} />
      </div>

      <div className="flex items-start justify-between">
        <AgentAvatar avatarUrl={agent.avatar_url} name={agent.name} />
        <Badge
          variant="secondary"
          className={cn(
            "text-[10px] px-1.5 py-0 h-5 mr-8",
            agent.status === "active" && "border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
            agent.status === "draft" && "border-border bg-muted text-muted-foreground",
            agent.status === "archived" && "border-border/70 bg-muted/60 text-muted-foreground"
          )}
        >
          {agent.status}
        </Badge>
      </div>
      <h3 className="mt-3 text-sm font-medium leading-tight text-foreground">
        {agent.name}
      </h3>
      <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {agent.description || "No description"}
      </p>

      <div className="mt-4 flex flex-wrap gap-2 mb-2">
        <Badge variant="secondary" className="h-5 px-2 py-0 text-[10px]">
          {findProvider(catalog?.providers, providerOfModel(agent.model_id))?.label ?? providerOfModel(agent.model_id)}
        </Badge>
        <Badge variant="secondary" className="h-5 px-2 py-0 font-mono text-[10px]">
          {modelDisplayName(catalog?.models, agent.model_id)}
        </Badge>
      </div>

      <div className="flex items-center justify-between border-t border-border/50 pt-2 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <CalendarDays className="h-3 w-3" />
          <span>{formatDate(agent.created_at)}</span>
        </div>
        <div className="flex items-center gap-1.5">
          {agent.is_published ? <Globe className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
          <span>{agent.is_published ? "Published" : "Private"}</span>
        </div>
        <MessageSquare className="h-3 w-3 transition-colors group-hover:text-foreground" />
      </div>
    </Link>
  );
}

/* ─── List Row ───────────────────────────────────────────────── */

function AgentListRow({ agent }: { agent: AgentListItem }) {
  const { data: catalog } = useModelCatalog();
  return (
    <Link
      href={`/agents/${agent.id}/chat`}
      className="group relative flex items-center gap-4 rounded-lg border border-transparent bg-card/60 px-4 py-2.5 transition-all hover:border-border hover:bg-card"
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary/20 bg-primary/10">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-medium truncate">{agent.name}</h3>
        <p className="truncate text-xs text-muted-foreground">
          {agent.description || "No description"}
        </p>
        <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
          <span className="rounded bg-muted px-1.5 py-0.5">
            {findProvider(catalog?.providers, providerOfModel(agent.model_id))?.label ?? providerOfModel(agent.model_id)}
          </span>
          <span className="font-mono">{modelDisplayName(catalog?.models, agent.model_id)}</span>
          <span className="inline-flex items-center gap-1">
            <CalendarDays className="h-3 w-3" />
            {formatDate(agent.created_at)}
          </span>
          <span className="inline-flex items-center gap-1">
            {agent.is_published ? <Globe className="h-3 w-3" /> : <Lock className="h-3 w-3" />}
            {agent.is_published ? "Published" : "Private"}
          </span>
        </div>
      </div>
      <Badge
        variant="secondary"
        className={cn(
          "text-[10px] px-1.5 py-0 h-5",
          agent.status === "active" && "border-emerald-500/30 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
          agent.status === "draft" && "border-border bg-muted text-muted-foreground",
          agent.status === "archived" && "border-border/70 bg-muted/60 text-muted-foreground"
        )}
      >
        {agent.status}
      </Badge>

      {/* Actions menu */}
      <div className="shrink-0">
        <AgentActionsMenu agent={agent} />
      </div>
    </Link>
  );
}
