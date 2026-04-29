"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ReactFlowProvider } from "@xyflow/react";
import {
  CheckCircle2, XCircle, Clock, Loader2, Play, Zap, ArrowLeft,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useWorkflow, useWorkflowRuns } from "../hooks/useWorkflows";
import type { NodeExecutionLog } from "../types";
import { ExecutionCanvas } from "../components/ExecutionCanvas";
import { ExecutionNDVModal } from "../components/ExecutionNDVModal";
import { cn } from "@/lib/utils";

interface WorkflowExecutionsViewProps {
  workflowId: string;
}

export function WorkflowExecutionsView({ workflowId }: WorkflowExecutionsViewProps) {
  const router = useRouter();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [openNodeId, setOpenNodeId] = useState<string | null>(null);

  const { data: workflow, isLoading: loadingWorkflow } = useWorkflow(workflowId);
  const { data: runs = [], isLoading: loadingRuns } = useWorkflowRuns(workflowId);

  // Auto-select the first run
  useEffect(() => {
    if (runs.length > 0 && !selectedRunId) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  const selectedRun = runs.find((r) => r.id === selectedRunId);

  // Build execution status map: nodeId → status
  const executionMap = useMemo(() => {
    const map = new Map<string, NodeExecutionLog>();
    for (const ne of selectedRun?.node_executions ?? []) {
      map.set(ne.node_id, ne);
    }
    return map;
  }, [selectedRun]);

  // Convert workflow nodes/edges to React Flow format
  const flowNodes = useMemo(() => {
    if (!workflow?.nodes) return [];
    return workflow.nodes.map((n) => ({
      id: n.id,
      type: "baseNode" as const,
      position: { x: n.position_x, y: n.position_y },
      // Seed size so MiniMap can place nodes immediately — React Flow v12 uses
      // `initialWidth/initialHeight` for pre-measurement hints. Fallback defaults
      // cover legacy rows that never persisted dimensions.
      initialWidth: n.width ?? 200,
      initialHeight: n.height ?? 70,
      data: {
        nodeType: n.node_type,
        label: n.label || "",
        config: n.config || {},
        // Execution overlay data
        _executionStatus: executionMap.get(n.id)?.status,
        _executionError: executionMap.get(n.id)?.error,
      },
    }));
  }, [workflow, executionMap]);

  const flowEdges = useMemo(() => {
    if (!workflow?.edges) return [];
    return workflow.edges.map((e) => ({
      id: e.id,
      source: e.source_node_id,
      target: e.target_node_id,
      ...(e.source_handle ? { sourceHandle: e.source_handle } : {}),
      ...(e.target_handle ? { targetHandle: e.target_handle } : {}),
      ...(e.label ? { label: e.label } : {}),
    }));
  }, [workflow]);

  const isLoading = loadingWorkflow || loadingRuns;

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border bg-background px-3 py-2">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5"
              onClick={() => router.push(`/workflows/${workflowId}`)}
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Editor
            </Button>
            <div className="h-4 w-px bg-border" />
            <span className="text-sm font-medium">{workflow?.name || "Untitled"}</span>
            <Badge variant="secondary" className="text-[10px]">Executions</Badge>
          </div>
        </div>

        {/* Split layout */}
        <div className="flex flex-1 overflow-hidden">
          {/* Left panel — Run list */}
          <div className="flex w-72 shrink-0 flex-col border-r border-border bg-card/50">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="text-xs font-semibold text-foreground">Executions</span>
              <span className="text-[10px] text-muted-foreground">{runs.length} runs</span>
            </div>

            <div className="flex-1 overflow-auto p-1.5">
              {runs.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Play className="h-8 w-8 text-muted-foreground/20 mb-3" />
                  <p className="text-xs text-muted-foreground">No executions yet</p>
                  <p className="text-[10px] text-muted-foreground/60 mt-1">Run the workflow to see results</p>
                </div>
              ) : (
                <div className="space-y-0.5">
                  {runs.map((run) => (
                    <button
                      key={run.id}
                      onClick={() => {
                        setSelectedRunId(run.id);
                        setOpenNodeId(null);
                      }}
                      className={cn(
                        "flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors",
                        selectedRunId === run.id
                          ? "bg-accent"
                          : "hover:bg-accent/50"
                      )}
                    >
                      {/* Status color bar */}
                      <div className={cn(
                        "w-0.5 self-stretch rounded-full shrink-0",
                        run.status === "completed" ? "bg-emerald-500" : run.status === "running" ? "bg-primary" : "bg-red-500"
                      )} />
                      {run.status === "running" ? (
                        <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-primary" />
                      ) : run.status === "completed" ? (
                        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-500" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 shrink-0 text-red-500" />
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium truncate">
                          {new Date(run.started_at).toLocaleString()}
                        </p>
                        <p className="text-[10px] text-muted-foreground truncate">
                          {run.status === "completed" ? "Succeeded" : run.status === "running" ? "Running" : "Failed"}
                          {run.completed_at && ` in ${Math.round((new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000)}s`}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right panel — Execution detail + canvas */}
          <div className="flex flex-1 flex-col overflow-hidden bg-background">
            {selectedRun ? (
              <>
                {/* Execution header */}
                <div className="border-b border-border px-5 py-2.5">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">
                      {new Date(selectedRun.started_at).toLocaleString()}
                    </span>
                    <Badge className={cn(
                      "text-[10px] h-5 px-1.5",
                      selectedRun.status === "completed"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30"
                        : "bg-red-50 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-300 dark:border-red-500/30"
                    )}>
                      {selectedRun.status === "completed" ? "Succeeded" : selectedRun.status}
                    </Badge>
                    {selectedRun.completed_at && (
                      <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {Math.round((new Date(selectedRun.completed_at).getTime() - new Date(selectedRun.started_at).getTime()) / 1000)}s
                      </span>
                    )}
                    {selectedRun.total_tokens > 0 && (
                      <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Zap className="h-3 w-3" />
                        {selectedRun.total_tokens} tokens
                      </span>
                    )}
                  </div>

                  {selectedRun.error_message && (
                    <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">
                      {selectedRun.error_message}
                    </p>
                  )}
                </div>

                {/* Canvas with execution overlay */}
                <div className="flex-1">
                  <ExecutionCanvas
                    nodes={flowNodes}
                    edges={flowEdges}
                    executionMap={executionMap}
                    onNodeClick={setOpenNodeId}
                  />
                </div>
              </>
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <Play className="h-10 w-10 text-muted-foreground/20 mb-3" />
                <p className="text-sm text-muted-foreground">Select an execution to view</p>
              </div>
            )}
          </div>
        </div>

        {/* NDV modal — shows input/output for the clicked execution node */}
        <ExecutionNDVModal
          open={!!openNodeId}
          execution={openNodeId ? executionMap.get(openNodeId) ?? null : null}
          onClose={() => setOpenNodeId(null)}
        />
      </div>
    </ReactFlowProvider>
  );
}
