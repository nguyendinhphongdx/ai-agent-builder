"use client";

import { useState } from "react";
import {
  CheckCircle2, XCircle, Clock, Loader2, ChevronRight,
  Play, Zap, ArrowLeft,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/status-badge";
import { ErrorState } from "@/components/ui/error-state";
import { useWorkflowRuns } from "../hooks/useWorkflows";
import type { WorkflowRun, NodeExecutionLog } from "../types";
import { cn } from "@/lib/utils";

interface ExecutionsPanelProps {
  workflowId: string;
}

export function ExecutionsPanel({ workflowId }: ExecutionsPanelProps) {
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const { data: runs = [], isLoading } = useWorkflowRuns(workflowId);

  const selectedRun = runs.find((r) => r.id === selectedRunId);
  const selectedNode = selectedRun?.node_executions?.find(
    (n) => n.node_id === selectedNodeId,
  );

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-1 overflow-hidden">
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
                    setSelectedNodeId(null);
                  }}
                  className={cn(
                    "flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-left transition-colors",
                    selectedRunId === run.id
                      ? "bg-accent"
                      : "hover:bg-accent/50"
                  )}
                >
                  {run.status === "completed" ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-success" />
                  ) : run.status === "running" ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
                  ) : (
                    <XCircle className="h-4 w-4 shrink-0 text-destructive" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">
                      {new Date(run.started_at).toLocaleString()}
                    </p>
                    <p className="text-[10px] text-muted-foreground truncate">
                      {run.node_executions?.length || 0} nodes
                      {run.total_tokens > 0 ? ` · ${run.total_tokens} tokens` : ""}
                    </p>
                  </div>
                  {run.completed_at && (
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                      {Math.round(
                        (new Date(run.completed_at).getTime() -
                          new Date(run.started_at).getTime()) / 1000
                      )}s
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right panel — Detail view */}
      <div className="flex flex-1 flex-col overflow-hidden bg-background">
        {!selectedRun ? (
          /* Empty state */
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-3">
              <ChevronRight className="h-5 w-5 text-muted-foreground/40" />
            </div>
            <p className="text-sm text-muted-foreground">Select an execution to view details</p>
          </div>
        ) : selectedNode ? (
          /* Node detail */
          <NodeDetailView
            node={selectedNode}
            onBack={() => setSelectedNodeId(null)}
          />
        ) : (
          /* Run detail — node execution list */
          <RunDetailView
            run={selectedRun}
            onSelectNode={setSelectedNodeId}
          />
        )}
      </div>
    </div>
  );
}

/* ─── Run detail: summary + node list ─── */
function RunDetailView({
  run,
  onSelectNode,
}: {
  run: WorkflowRun;
  onSelectNode: (id: string) => void;
}) {
  const nodes = run.node_executions || [];

  return (
    <div className="flex h-full flex-col">
      {/* Run header */}
      <div className="border-b border-border px-5 py-3">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "h-2.5 w-2.5 rounded-full",
              run.status === "completed" ? "bg-success" : "bg-destructive"
            )}
          />
          <span className="text-sm font-medium">
            {new Date(run.started_at).toLocaleString()}
          </span>
          <StatusBadge tone={run.status === "completed" ? "active" : "failed"}>
            {run.status}
          </StatusBadge>
        </div>
        <div className="mt-1.5 flex items-center gap-4 text-[11px] text-muted-foreground">
          <span>{nodes.length} nodes executed</span>
          {run.total_tokens > 0 && (
            <span className="flex items-center gap-1">
              <Zap className="h-3 w-3" />{run.total_tokens} tokens
            </span>
          )}
          {run.completed_at && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {Math.round(
                (new Date(run.completed_at).getTime() -
                  new Date(run.started_at).getTime()) / 1000
              )}s total
            </span>
          )}
        </div>
      </div>

      {/* Node list */}
      <div className="flex-1 overflow-auto p-3">
        {nodes.length === 0 ? (
          <p className="p-4 text-xs text-muted-foreground text-center">No node executions recorded</p>
        ) : (
          <div className="space-y-1">
            {nodes.map((node, i) => (
              <button
                key={node.node_id + i}
                onClick={() => onSelectNode(node.node_id)}
                className="flex w-full items-center gap-3 rounded-lg border border-border bg-card px-4 py-3 text-left transition-colors hover:bg-accent group"
              >
                <div className={cn(
                  "flex h-7 w-7 items-center justify-center rounded-lg text-[11px] font-bold",
                  node.status === "completed"
                    ? "bg-success/15 text-success"
                    : "bg-destructive/15 text-destructive"
                )}>
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">
                    {node.label || node.node_type}
                  </p>
                  <p className="text-[10px] text-muted-foreground">{node.node_type}</p>
                </div>
                {node.tokens_used > 0 && (
                  <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Zap className="h-2.5 w-2.5" />{node.tokens_used}
                  </span>
                )}
                {node.started_at && node.completed_at && (
                  <span className="text-[10px] text-muted-foreground">
                    {Math.round(
                      new Date(node.completed_at).getTime() -
                        new Date(node.started_at).getTime()
                    )}ms
                  </span>
                )}
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
              </button>
            ))}
          </div>
        )}

        {/* Error message */}
        {run.error_message && (
          <ErrorState
            title="Error"
            message={run.error_message}
            className="mt-3"
          />
        )}
      </div>
    </div>
  );
}

/* ─── Node detail: input/output ─── */
function NodeDetailView({
  node,
  onBack,
}: {
  node: NodeExecutionLog;
  onBack: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-2.5 border-b border-border px-5 py-2.5">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onBack}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div
          className={cn(
            "h-2 w-2 rounded-full",
            node.status === "completed" ? "bg-success" : "bg-destructive"
          )}
        />
        <span className="text-sm font-medium">
          {node.label || node.node_type}
        </span>
        <Badge variant="secondary" className="text-[10px] h-5 px-1.5">
          {node.node_type}
        </Badge>
      </div>

      {/* Content — two-column input/output */}
      <div className="flex-1 overflow-auto">
        {/* Status bar */}
        <div className="flex items-center gap-4 px-5 py-3 text-xs text-muted-foreground border-b border-border">
          <span className="flex items-center gap-1">
            {node.status === "completed"
              ? <CheckCircle2 className="h-3.5 w-3.5 text-success" />
              : <XCircle className="h-3.5 w-3.5 text-destructive" />
            }
            {node.status}
          </span>
          {node.tokens_used > 0 && (
            <span className="flex items-center gap-1">
              <Zap className="h-3 w-3" />
              {node.tokens_used} tokens
            </span>
          )}
          {node.started_at && node.completed_at && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {Math.round(
                new Date(node.completed_at).getTime() -
                  new Date(node.started_at).getTime()
              )}ms
            </span>
          )}
        </div>

        {/* Input / Output side by side */}
        <div className="grid grid-cols-2 divide-x divide-border h-full">
          <div className="flex flex-col p-4">
            <h4 className="mb-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Input</h4>
            <pre className="flex-1 rounded-lg border border-border bg-muted/50 p-3 text-xs font-mono overflow-auto whitespace-pre-wrap">
              {JSON.stringify(node.input_items, null, 2) || "—"}
            </pre>
          </div>
          <div className="flex flex-col p-4">
            <h4 className="mb-2 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Output</h4>
            <pre className={cn(
              "flex-1 rounded-lg border p-3 text-xs font-mono overflow-auto whitespace-pre-wrap",
              node.status === "completed"
                ? "border-success/40 bg-success/5"
                : "border-destructive/40 bg-destructive/5"
            )}>
              {node.error
                ? node.error
                : JSON.stringify(node.output_items, null, 2) || "—"
              }
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
}
