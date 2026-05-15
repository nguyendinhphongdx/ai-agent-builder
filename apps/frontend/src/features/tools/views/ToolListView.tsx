"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import {
  Plus,
  Wrench,
  Globe,
  Code,
  Database,
  Search,
  MoreHorizontal,
  Trash2,
  ExternalLink,
  Power,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTools, useDeleteTool, useUpdateTool } from "../hooks/useTools";
import { TOOL_TYPE_META, type Tool, type ToolType } from "../types";
import { useWorkspacePath } from "@/features/workspaces";
import { cn } from "@/lib/utils";

const ICON_MAP: Record<string, typeof Globe> = {
  globe: Globe,
  code: Code,
  database: Database,
  wrench: Wrench,
};

const COLOR_MAP: Record<string, string> = {
  blue: "bg-blue-50 text-blue-600 border-blue-200",
  violet: "bg-violet-50 text-violet-600 border-violet-200",
  emerald: "bg-emerald-50 text-emerald-600 border-emerald-200",
  amber: "bg-amber-50 text-amber-600 border-amber-200",
  rose: "bg-rose-50 text-rose-600 border-rose-200",
};

const TYPE_FILTERS: Array<"all" | ToolType> = [
  "all",
  "http_request",
  "code_exec",
  "db_query",
  "web_scrape",
  "custom_function",
];

export function ToolListView() {
  const wp = useWorkspacePath();
  const { data: tools, isLoading } = useTools();
  const deleteTool = useDeleteTool();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [typeFilter, setTypeFilter] = useState<"all" | ToolType>("all");

  const filteredTools = useMemo(() => {
    if (!tools) return [];
    return tools.filter((tool) => {
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        tool.name.toLowerCase().includes(q) ||
        tool.description.toLowerCase().includes(q);
      const matchesStatus =
        statusFilter === "all" || (statusFilter === "active" ? tool.is_active : !tool.is_active);
      const matchesType = typeFilter === "all" || tool.tool_type === typeFilter;
      return matchesSearch && matchesStatus && matchesType;
    });
  }, [tools, search, statusFilter, typeFilter]);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="mb-6 h-8 w-48 animate-pulse rounded-lg bg-muted" />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-muted/70" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-linear-to-b flex h-full flex-col from-background via-background to-muted/20">
      <div className="flex items-center justify-between border-b border-border/70 bg-background/80 px-6 py-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">Tools</h1>
          <span className="text-xs text-muted-foreground">{tools?.length ?? 0} tools</span>
        </div>
        <Link href={wp("/tools/new")}>
          <Button size="sm" className="gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            New Tool
          </Button>
        </Link>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-b border-border/70 bg-background/50 px-6 py-2.5">
        <div className="relative w-full max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search tools..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-8 border-border bg-muted/60 pl-8 text-sm"
          />
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-border/70 bg-muted/50 p-0.5">
          {(["all", "active", "inactive"] as const).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={cn(
                "rounded-md px-2.5 py-1 text-[11px] font-medium capitalize transition-colors",
                statusFilter === status
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {status}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-1 rounded-lg border border-border/70 bg-muted/50 p-0.5">
          {TYPE_FILTERS.map((type) => (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              className={cn(
                "rounded-md px-2.5 py-1 text-[11px] font-medium transition-colors",
                typeFilter === type
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {type === "all" ? "All types" : TOOL_TYPE_META[type].label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 p-6">
        {!tools?.length ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-primary/20 bg-primary/10">
              <Wrench className="h-6 w-6 text-primary" />
            </div>
            <p className="text-sm text-muted-foreground">No tools yet</p>
            <Link href={wp("/tools/new")}>
              <Button size="sm" className="mt-4 gap-1.5">
                <Plus className="h-3.5 w-3.5" />
                Create your first tool
              </Button>
            </Link>
          </div>
        ) : !filteredTools.length ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-sm text-muted-foreground">No tools match current filters</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTools.map((tool) => (
              <ToolRow
                key={tool.id}
                tool={tool}
                onDelete={() => deleteTool.mutate(tool.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolRow({
  tool,
  onDelete,
}: {
  tool: Tool;
  onDelete: () => void;
}) {
  const router = useRouter();
  const wp = useWorkspacePath();
  const updateTool = useUpdateTool(tool.id);
  const meta = TOOL_TYPE_META[tool.tool_type];
  const Icon = ICON_MAP[meta?.icon ?? "wrench"] ?? Wrench;
  const colorClasses = COLOR_MAP[meta?.color ?? "blue"] ?? COLOR_MAP.blue;
  const iconBg = colorClasses.split(" ")[0];
  const iconText = colorClasses.split(" ")[1];

  return (
    <Link
      href={wp(`/tools/${tool.id}`)}
      className="group flex w-full items-center gap-4 rounded-xl border border-border/70 bg-card/70 px-4 py-3 text-left transition-all hover:border-primary/30 hover:bg-card"
    >
      <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg border", iconBg)}>
        <Icon className={cn("h-4 w-4", iconText)} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h3 className="truncate text-sm font-medium">{tool.name}</h3>
          <Badge variant="secondary" className="h-5 border-border bg-muted px-1.5 py-0 text-[10px] text-muted-foreground">
            {meta?.label ?? tool.tool_type}
          </Badge>
        </div>
        <p className="truncate text-xs text-muted-foreground">{tool.description}</p>
      </div>
      <div className="flex items-center gap-2">
        {tool.is_active ? (
          <Badge className="h-5 border-emerald-500/30 bg-emerald-500/15 px-1.5 text-[10px] text-emerald-700 dark:text-emerald-300">
            Active
          </Badge>
        ) : (
          <Badge variant="secondary" className="h-5 border-border bg-muted px-1.5 text-[10px] text-muted-foreground">
            Inactive
          </Badge>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-xs"
              className="opacity-0 transition-opacity group-hover:opacity-100"
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); }}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                updateTool.mutate({ is_active: !tool.is_active });
              }}
            >
              <Power className="mr-2 h-3.5 w-3.5" />
              {tool.is_active ? "Set inactive" : "Set active"}
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                router.push(wp(`/tools/${tool.id}`));
              }}
            >
                <ExternalLink className="mr-2 h-3.5 w-3.5" />
                Open detail page
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onDelete();
              }}
              className="text-red-500"
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
