"use client";

import { useEffect, useState, useCallback } from "react";
import { Bot, ChevronDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { agentService } from "@/features/agents/services/agentService";
import type { AgentListItem } from "@/features/agents/types";

interface AgentPickerProps {
  value: string | null;
  onChange: (agentId: string | null) => void;
  label?: string;
}

/**
 * Dropdown picker for the user's agents — used by integrations that target
 * a specific agent (embed widget, share link). Auto-selects when only one
 * agent exists so the next step lights up immediately.
 */
export function AgentPicker({
  value,
  onChange,
  label = "Choose an agent",
}: AgentPickerProps) {
  const [agents, setAgents] = useState<AgentListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setAgents(await agentService.list());
    } catch {
      setAgents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Auto-select if exactly 1 agent exists.
  useEffect(() => {
    if (!loading && !value && agents.length === 1) {
      onChange(agents[0].id);
    }
  }, [loading, value, agents, onChange]);

  const selected = agents.find((a) => a.id === value) ?? null;

  if (loading) {
    return (
      <div className="flex h-9 items-center gap-2 rounded-md border border-border bg-muted/30 px-3 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /> Loading agents…
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-[11px] text-amber-700 dark:text-amber-300">
        Bạn chưa có agent nào. Vào{" "}
        <a href={"/ws/agents"} className="font-medium underline">
          Agents
        </a>{" "}
        để tạo trước, rồi quay lại đây.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <label className="text-[11px] font-medium text-muted-foreground">
        {label}
      </label>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            className="h-9 w-full justify-between gap-2 px-3 text-xs"
          >
            <span className="flex min-w-0 items-center gap-2">
              <Bot className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">
                {selected?.name ?? "Select agent…"}
              </span>
            </span>
            <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="start"
          className="w-[--radix-dropdown-menu-trigger-width] min-w-72"
        >
          {agents.map((a) => (
            <DropdownMenuItem
              key={a.id}
              onClick={() => onChange(a.id)}
              className={cn(
                "flex flex-col items-start gap-0.5 py-2",
                a.id === value && "bg-accent",
              )}
            >
              <span className="text-xs font-medium">{a.name}</span>
              <span className="font-mono text-[10px] text-muted-foreground">
                {a.model_id}
              </span>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
