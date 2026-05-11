"use client";

import { useState } from "react";
import Link from "next/link";
import { Building2, Check, ChevronDown, Plus, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { useWorkspaces } from "../hooks/useWorkspaces";
import { useWorkspaceStore } from "../stores/workspaceStore";
import { CreateWorkspaceDialog } from "./CreateWorkspaceDialog";

/**
 * Header dropdown for switching active workspace. Auto-selects the
 * caller's personal workspace on first load (via useWorkspaces side
 * effect) and persists choice across page loads via the zustand store.
 *
 * Switching workspaces invalidates every cached query so the next
 * fetch sends the new ``X-Workspace-Id`` header.
 */
export function WorkspaceSwitcher() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const currentId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const setCurrent = useWorkspaceStore((s) => s.setCurrentWorkspaceId);
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);

  const current = workspaces?.find((w) => w.id === currentId) ?? null;

  const onSelect = (id: string) => {
    if (id === currentId) return;
    setCurrent(id);
    // Drop every cached query — the next fetch will send the new
    // workspace header and the BE will return tenant-scoped data.
    qc.invalidateQueries();
  };

  if (isLoading || !workspaces || workspaces.length === 0) {
    return (
      <div className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-muted/40 px-2.5 text-xs text-muted-foreground">
        <Building2 className="h-3.5 w-3.5" />
        <span>Loading…</span>
      </div>
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="h-8 gap-1.5 px-2.5 text-xs font-medium"
          >
            <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="max-w-[10rem] truncate">
              {current?.name ?? "Select workspace"}
            </span>
            <ChevronDown className="h-3.5 w-3.5 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuLabel className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Workspaces
          </DropdownMenuLabel>
          {workspaces.map((w) => (
            <DropdownMenuItem
              key={w.id}
              onClick={() => onSelect(w.id)}
              className="flex items-start gap-2 py-2"
            >
              <Building2
                className={cn(
                  "mt-0.5 h-3.5 w-3.5 shrink-0",
                  w.id === currentId ? "text-primary" : "text-muted-foreground",
                )}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-xs font-medium">{w.name}</span>
                  {w.is_personal && (
                    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-muted-foreground">
                      personal
                    </span>
                  )}
                </div>
                <div className="truncate text-[10px] text-muted-foreground">
                  {w.organization.name} · {w.role}
                </div>
              </div>
              {w.id === currentId && (
                <Check className="mt-1 h-3 w-3 shrink-0 text-primary" />
              )}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            Create workspace
          </DropdownMenuItem>
          {current && !current.is_personal && (
            <DropdownMenuItem asChild>
              <Link href="/settings/workspace" className="cursor-pointer">
                <Settings2 className="mr-2 h-3.5 w-3.5" />
                Workspace settings
              </Link>
            </DropdownMenuItem>
          )}
        </DropdownMenuContent>
      </DropdownMenu>
      <CreateWorkspaceDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}
