"use client";

import { useState } from "react";
import Link from "next/link";
import { Building2, Check, ChevronDown, Layers, Loader2, Plus } from "lucide-react";
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
import { cn } from "@/lib/utils";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { sessionService } from "@/lib/api/sessionService";
import { useWorkspaces } from "../hooks/useWorkspaces";
import { useWorkspaceStore } from "../stores/workspaceStore";
import { CreateWorkspaceDialog } from "./CreateWorkspaceDialog";

/**
 * Header dropdown for switching active workspace.
 *
 * Phase 1 of the Hub auth refactor (docs/architecture/
 * hub-auth-refactor.md): each item POSTs ``/api/auth/enter-workspace``
 * which mints a workspace-scoped access_token cookie with the
 * workspace id baked in. We keep the localStorage write for backward
 * compat with code paths still reading the zustand store; Phase 3
 * deletes that store.
 *
 * The new token replaces the old in the same cookie slot, so all
 * subsequent requests automatically carry the right workspace
 * claims. ``qc.invalidateQueries()`` flushes any data fetched under
 * the old context.
 */
export function WorkspaceSwitcher() {
  const { data: workspaces, isLoading } = useWorkspaces();
  const currentId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const setCurrent = useWorkspaceStore((s) => s.setCurrentWorkspaceId);
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);

  const current = workspaces?.find((w) => w.id === currentId) ?? null;

  const enter = useMutation({
    mutationFn: (workspace_id: string) => sessionService.enter(workspace_id),
    onSuccess: (data) => {
      // Keep zustand in sync for legacy consumers. Phase 3 deletes
      // this assignment along with the store itself.
      setCurrent(data.workspace_id);
      // Drop every cached query — the next fetch goes through the
      // new workspace_token automatically.
      qc.invalidateQueries();
    },
    onError: (e) => {
      const msg =
        (e as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Switch failed";
      toast.error(typeof msg === "string" ? msg : "Switch failed");
    },
  });

  const onSelect = (id: string) => {
    if (id === currentId) return;
    enter.mutate(id);
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
              {enter.isPending && enter.variables === w.id ? (
                <Loader2 className="mt-1 h-3 w-3 shrink-0 animate-spin text-muted-foreground" />
              ) : w.id === currentId ? (
                <Check className="mt-1 h-3 w-3 shrink-0 text-primary" />
              ) : null}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-3.5 w-3.5" />
            Create workspace
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/org/workspaces" className="cursor-pointer">
              <Layers className="mr-2 h-3.5 w-3.5" />
              Manage in Org
            </Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <CreateWorkspaceDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}
