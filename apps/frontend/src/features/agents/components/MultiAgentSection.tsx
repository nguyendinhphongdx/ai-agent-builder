"use client";

import { useState } from "react";
import { Plus, X, Bot, Crown, ArrowRightLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { useAgents } from "../hooks/useAgents";
import { cn } from "@/lib/utils";

type CollabMode = "none" | "supervisor" | "peer";

interface MultiAgentSectionProps {
  currentAgentId?: string;
  mode: CollabMode;
  workerIds: string[];
  onModeChange: (mode: CollabMode) => void;
  onWorkersChange: (ids: string[]) => void;
}

export function MultiAgentSection({
  currentAgentId,
  mode,
  workerIds,
  onModeChange,
  onWorkersChange,
}: MultiAgentSectionProps) {
  const { data: allAgents } = useAgents();
  const [showPicker, setShowPicker] = useState(false);

  const availableAgents = (allAgents ?? []).filter(
    (a) => a.id !== currentAgentId && !workerIds.includes(a.id)
  );

  const selectedAgents = (allAgents ?? []).filter((a) =>
    workerIds.includes(a.id)
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-foreground/70">
          Multi-Agent
        </label>
        <Badge
          variant="secondary"
          className="text-[9px] h-4 px-1.5 bg-muted text-muted-foreground"
        >
          Optional
        </Badge>
      </div>

      {/* Mode selector */}
      <div className="flex gap-2">
        {(
          [
            { value: "none", label: "Single", icon: Bot, desc: "Standalone agent" },
            { value: "supervisor", label: "Supervisor", icon: Crown, desc: "Delegates to workers" },
            { value: "peer", label: "Peer", icon: ArrowRightLeft, desc: "Collaborate equally" },
          ] as const
        ).map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => {
              onModeChange(opt.value);
              if (opt.value === "none") onWorkersChange([]);
            }}
            className={cn(
              "flex-1 flex flex-col items-center gap-1.5 rounded-lg border p-3 transition-all",
              mode === opt.value
                ? "border-primary/30 bg-primary/10"
                : "border-border bg-muted/50 hover:border-border"
            )}
          >
            <opt.icon
              className={cn(
                "h-4 w-4",
                mode === opt.value ? "text-primary" : "text-muted-foreground"
              )}
            />
            <span className="text-[11px] font-medium">{opt.label}</span>
            <span className="text-[9px] text-muted-foreground">{opt.desc}</span>
          </button>
        ))}
      </div>

      {/* Worker agents */}
      {mode !== "none" && (
        <div className="space-y-2 mt-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-muted-foreground">
              {mode === "supervisor" ? "Worker Agents" : "Peer Agents"}
            </span>
            <button
              type="button"
              onClick={() => setShowPicker(!showPicker)}
              className="text-[11px] text-primary hover:text-primary/80"
            >
              <Plus className="inline h-3 w-3 mr-0.5" />
              Add Agent
            </button>
          </div>

          {/* Selected workers */}
          {selectedAgents.length > 0 && (
            <div className="space-y-1.5">
              {selectedAgents.map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-center gap-2.5 rounded-lg bg-muted/50 px-3 py-2"
                >
                  <div className="flex h-6 w-6 items-center justify-center rounded-md bg-muted">
                    <Bot className="h-3 w-3 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{agent.name}</p>
                    <p className="text-[10px] text-muted-foreground truncate">
                      {agent.llm_model}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      onWorkersChange(workerIds.filter((id) => id !== agent.id))
                    }
                    className="text-muted-foreground/50 hover:text-foreground"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Agent picker dropdown */}
          {showPicker && availableAgents.length > 0 && (
            <div className="rounded-lg border border-border bg-popover p-1 space-y-0.5">
              {availableAgents.map((agent) => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => {
                    onWorkersChange([...workerIds, agent.id]);
                    setShowPicker(false);
                  }}
                  className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-left hover:bg-accent"
                >
                  <div className="flex h-5 w-5 items-center justify-center rounded bg-muted">
                    <Bot className="h-2.5 w-2.5 text-muted-foreground" />
                  </div>
                  <span className="text-xs">{agent.name}</span>
                  <span className="ml-auto text-[10px] text-muted-foreground">
                    {agent.llm_model}
                  </span>
                </button>
              ))}
            </div>
          )}

          {selectedAgents.length === 0 && !showPicker && (
            <p className="text-[11px] text-muted-foreground py-2">
              No agents added yet. Add agents to enable collaboration.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
