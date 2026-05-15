"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ReactFlowProvider } from "@xyflow/react";
import { Check, Loader2, Plus, History, Settings } from "lucide-react";
import { Canvas } from "../components/Canvas";
import { NodePalette } from "../components/NodePalette";
import { NDVModal } from "../components/ndv/NDVModal";
import { WorkflowToolbar } from "../components/WorkflowToolbar";
import { RunWorkflowDialog } from "../components/RunWorkflowDialog";
import { useWorkflow, useSaveWorkflow, useExecuteWorkflow } from "../hooks/useWorkflows";
import { useWorkflowSocket } from "../hooks/useWorkflowSocket";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";
import { WorkflowEditorProvider } from "../lib/editor-context";
import type { WorkflowSaveInput, WorkflowNodeType } from "../types";
import { Button } from "@/components/ui/button";

interface WorkflowEditorViewProps {
  workflowId: string;
}

const AUTOSAVE_DELAY_MS = 2000;
const SAVED_INDICATOR_MS = 1500;

export function WorkflowEditorView({ workflowId }: WorkflowEditorViewProps) {
  const router = useRouter();
  const { data: workflow, isLoading } = useWorkflow(workflowId);

  // Join socket room for real-time node execution tracking
  useWorkflowSocket(workflowId);
  const saveWorkflow = useSaveWorkflow(workflowId);
  const executeWorkflow = useExecuteWorkflow(workflowId);
  const store = useWorkflowEditorStore();
  const nameInputRef = useRef<HTMLInputElement>(null);
  const hydratedFor = useRef<string | null>(null);
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    if (!workflow) return;
    // Hydrate the editor store once per workflow id. Without this, a refetch
    // (window-focus, mount remount) would clobber unsaved edits.
    if (hydratedFor.current === workflow.id) return;
    hydratedFor.current = workflow.id;

    const nodes = (workflow.nodes || []).map((n) => ({
      id: n.id,
      type: "baseNode" as const,
      position: { x: n.position_x, y: n.position_y },
      data: { nodeType: n.node_type, label: n.label || "", config: n.config || {} },
    }));

    const edges = (workflow.edges || []).map((e) => ({
      id: e.id,
      type: "customEdge" as const,
      source: e.source_node_id,
      target: e.target_node_id,
      ...(e.source_handle ? { sourceHandle: e.source_handle } : {}),
      ...(e.target_handle ? { targetHandle: e.target_handle } : {}),
      ...(e.label ? { label: e.label } : {}),
    }));

    if (nodes.length === 0) {
      nodes.push({
        id: crypto.randomUUID(),
        type: "baseNode" as const,
        position: { x: 250, y: 250 },
        data: { nodeType: "start", label: "", config: {} },
      });
    }

    store.setNodes(nodes);
    store.setEdges(edges);
    store.setDirty(false);
  }, [workflow, store]);

  const handleSave = useCallback(() => {
    // Store nodes carry xyflow's generic shape; map them to the persistence
    // schema. nodeType is set by addNode/setNodes — always a WorkflowNodeType.
    const payload: WorkflowSaveInput = {
      nodes: store.nodes.map((n) => ({
        id: n.id,
        node_type: n.data.nodeType as WorkflowNodeType,
        label: (n.data.label as string) || null,
        config: (n.data.config as Record<string, unknown>) || {},
        position_x: n.position.x,
        position_y: n.position.y,
        width: n.measured?.width ?? null,
        height: n.measured?.height ?? null,
      })),
      edges: store.edges.map((e) => ({
        id: e.id,
        source_node_id: e.source,
        target_node_id: e.target,
        source_handle: e.sourceHandle || null,
        target_handle: e.targetHandle || null,
        label: (e.label as string) || null,
        style: {},
      })),
    };

    saveWorkflow.mutate(payload, {
      onSuccess: () => {
        store.setDirty(false);
        setShowSaved(true);
      },
    });
  }, [store, saveWorkflow]);

  // Autosave: 2s after the last edit, when there's something to save and we
  // aren't already in flight. The `isDirty + nodes + edges` deps make every
  // change reset the timer; the cleanup cancels in-flight autosaves on unmount
  // or when the user clicks the manual Save button (which clears isDirty).
  useEffect(() => {
    if (!store.isDirty || saveWorkflow.isPending) return;
    const id = window.setTimeout(handleSave, AUTOSAVE_DELAY_MS);
    return () => window.clearTimeout(id);
  }, [store.isDirty, store.nodes, store.edges, saveWorkflow.isPending, handleSave]);

  // Auto-clear the "Saved" indicator after a beat.
  useEffect(() => {
    if (!showSaved) return;
    const id = window.setTimeout(() => setShowSaved(false), SAVED_INDICATOR_MS);
    return () => window.clearTimeout(id);
  }, [showSaved]);

  const handleRun = () => {
    setRunDialogOpen(true);
  };

  const handleConfirmRun = (inputData: Record<string, unknown>) => {
    executeWorkflow.mutate(
      { input_data: inputData },
      { onSuccess: () => setRunDialogOpen(false) },
    );
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <WorkflowEditorProvider workflowId={workflowId}>
    <ReactFlowProvider>
      <div className="flex h-full flex-col">
        {/* Toolbar */}
        <div className="flex items-center justify-between border-b border-border bg-background px-3 py-2">
          <div className="flex items-center gap-4">
            <input
              ref={nameInputRef}
              defaultValue={workflow?.name || "Untitled"}
              onBlur={(e) => {
                const val = e.target.value.trim();
                if (val && val !== workflow?.name) {
                  saveWorkflow.mutate({ name: val });
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") (e.target as HTMLInputElement).blur();
              }}
              className="bg-transparent text-sm font-medium outline-none border-b border-transparent hover:border-border focus:border-primary px-0.5 py-0 w-auto max-w-48"
              style={{ width: `${Math.max(4, (workflow?.name?.length ?? 8)) * 0.55 + 1}rem` }}
            />
            <SaveIndicator
              isDirty={store.isDirty}
              isSaving={saveWorkflow.isPending}
              showSaved={showSaved}
            />
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-muted-foreground"
              onClick={() => router.push(`/ws/workflows/${workflowId}/executions`)}
            >
              <History className="h-3.5 w-3.5" />
              Executions
            </Button>

            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-muted-foreground"
              onClick={() => router.push(`/ws/workflows/${workflowId}/settings`)}
            >
              <Settings className="h-3.5 w-3.5" />
              Settings
            </Button>

            <WorkflowToolbar
              onSave={handleSave}
              onRun={handleRun}
              isSaving={saveWorkflow.isPending}
              workflowName=""
            />
          </div>
        </div>

        {/* Canvas */}
        <div className="relative flex-1 overflow-hidden">
          <Canvas />

          {/* Add node button */}
          <button
            onClick={() => store.openNodePalette()}
            className="absolute right-4 top-4 z-30 flex h-9 w-9 items-center justify-center rounded-lg border border-border bg-background shadow-md transition-colors hover:bg-accent"
            title="Add node"
          >
            <Plus className="h-4 w-4" />
          </button>

          {/* Node palette panel */}
          <NodePalette />
        </div>

        <NDVModal workflowId={workflowId} />

        <RunWorkflowDialog
          workflowId={workflowId}
          open={runDialogOpen}
          onOpenChange={setRunDialogOpen}
          onRun={handleConfirmRun}
          isRunning={executeWorkflow.isPending}
        />
      </div>
    </ReactFlowProvider>
    </WorkflowEditorProvider>
  );
}

/** Three-state pill: dirty (amber dot) → saving (spinner) → saved (green check). */
function SaveIndicator({
  isDirty,
  isSaving,
  showSaved,
}: {
  isDirty: boolean;
  isSaving: boolean;
  showSaved: boolean;
}) {
  if (isSaving) {
    return (
      <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        Saving…
      </span>
    );
  }
  if (showSaved && !isDirty) {
    return (
      <span className="flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400">
        <Check className="h-3 w-3" />
        Saved
      </span>
    );
  }
  if (isDirty) {
    return (
      <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        Unsaved
      </span>
    );
  }
  return null;
}
