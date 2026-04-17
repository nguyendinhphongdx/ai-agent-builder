"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ReactFlowProvider } from "@xyflow/react";
import { Loader2, Plus, History } from "lucide-react";
import { Canvas } from "../components/Canvas";
import { NodePalette } from "../components/NodePalette";
import { NDVModal } from "../components/ndv/NDVModal";
import { WorkflowToolbar } from "../components/WorkflowToolbar";
import { useWorkflow, useSaveWorkflow, useExecuteWorkflow } from "../hooks/useWorkflows";
import { useWorkflowSocket } from "../hooks/useWorkflowSocket";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";
import { Button } from "@/components/ui/button";

interface WorkflowEditorViewProps {
  workflowId: string;
}

export function WorkflowEditorView({ workflowId }: WorkflowEditorViewProps) {
  const router = useRouter();
  const { data: workflow, isLoading } = useWorkflow(workflowId);

  // Join socket room for real-time node execution tracking
  useWorkflowSocket(workflowId);
  const saveWorkflow = useSaveWorkflow(workflowId);
  const executeWorkflow = useExecuteWorkflow(workflowId);
  const store = useWorkflowEditorStore();
  const nameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!workflow) return;

    const nodes = (workflow.nodes || []).map((n) => ({
      id: n.id,
      type: "baseNode" as const,
      position: { x: n.position_x, y: n.position_y },
      data: { nodeType: n.node_type, label: n.label || "", config: n.config || {} },
    }));

    const edges = (workflow.edges || []).map((e) => ({
      id: e.id,
      source: e.source_node_id,
      target: e.target_node_id,
      ...(e.source_handle ? { sourceHandle: e.source_handle } : {}),
      ...(e.target_handle ? { targetHandle: e.target_handle } : {}),
      ...(e.label ? { label: e.label } : {}),
    }));

    // Auto-create Start node if workflow is empty
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
  }, [workflow]);

  const handleSave = () => {
    const nodes = store.nodes.map((n) => ({
      id: n.id,
      node_type: n.data.nodeType as string,
      label: (n.data.label as string) || null,
      config: (n.data.config as Record<string, unknown>) || {},
      position_x: n.position.x,
      position_y: n.position.y,
      width: n.measured?.width ?? null,
      height: n.measured?.height ?? null,
    }));

    const edges = store.edges.map((e) => ({
      id: e.id,
      source_node_id: e.source,
      target_node_id: e.target,
      source_handle: e.sourceHandle || null,
      target_handle: e.targetHandle || null,
      label: (e.label as string) || null,
      style: {},
    }));

    saveWorkflow.mutate({ nodes, edges } as any, {
      onSuccess: () => store.setDirty(false),
    });
  };

  const handleRun = () => {
    executeWorkflow.mutate(
      { message: "Hello" },
      {
        onSuccess: () => router.push(`/workflows/${workflowId}/executions`),
      }
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
                  saveWorkflow.mutate({ name: val } as any);
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") (e.target as HTMLInputElement).blur();
              }}
              className="bg-transparent text-sm font-medium outline-none border-b border-transparent hover:border-border focus:border-primary px-0.5 py-0 w-auto max-w-48"
              style={{ width: `${Math.max(4, (workflow?.name?.length ?? 8)) * 0.55 + 1}rem` }}
            />
            {store.isDirty && <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-muted-foreground"
              onClick={() => router.push(`/workflows/${workflowId}/executions`)}
            >
              <History className="h-3.5 w-3.5" />
              Executions
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

        <NDVModal />
      </div>
    </ReactFlowProvider>
  );
}
