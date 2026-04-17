"use client";

import { createElement, useState } from "react";
import { Settings, SlidersHorizontal, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getNodeEntry } from "../../nodes/registry";
import type { NodeData } from "../../nodes/types";
import { useWorkflowEditorStore } from "../../stores/workflowEditorStore";

interface NodeSettingsPanelProps {
  nodeId: string;
  data: NodeData;
}

type SettingsTab = "parameters" | "settings";

export function NodeSettingsPanel({ nodeId, data }: NodeSettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>("parameters");
  const { updateNodeData, removeNode } = useWorkflowEditorStore();
  const entry = getNodeEntry(data.nodeType);
  if (!entry) return null;

  const typeDef = entry.definition;

  return (
    <div className="flex h-full flex-col">
      {/* Tabs */}
      <div className="flex items-center gap-4 border-b border-border px-4 py-2">
        <button
          onClick={() => setActiveTab("parameters")}
          className={cn(
            "flex items-center gap-1.5 border-b-2 pb-1 text-xs font-medium transition-colors",
            activeTab === "parameters"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <SlidersHorizontal className="h-3 w-3" />
          Parameters
        </button>
        <button
          onClick={() => setActiveTab("settings")}
          className={cn(
            "flex items-center gap-1.5 border-b-2 pb-1 text-xs font-medium transition-colors",
            activeTab === "settings"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          )}
        >
          <Settings className="h-3 w-3" />
          Settings
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === "parameters" ? (
          <div className="space-y-5">
            {/* Per-node panel from registry */}
            {createElement(entry.panel, { id: nodeId, data })}
          </div>
        ) : (
          <div className="space-y-5">
            {/* Node label */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Node Name
              </label>
              <Input
                value={data.label || ""}
                onChange={(e) => updateNodeData(nodeId, { label: e.target.value })}
                placeholder={typeDef.label}
              />
            </div>

            {/* Description */}
            <div className="rounded-lg border border-border bg-muted/30 p-3">
              <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
                About this node
              </p>
              <p className="text-xs text-muted-foreground">
                {typeDef.description}
              </p>
            </div>

            {/* Delete */}
            {typeDef.canDelete !== false && (
              <div className="pt-4 border-t border-border">
                <Button
                  variant="destructive"
                  size="sm"
                  className="w-full gap-1.5"
                  onClick={() => removeNode(nodeId)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete Node
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
