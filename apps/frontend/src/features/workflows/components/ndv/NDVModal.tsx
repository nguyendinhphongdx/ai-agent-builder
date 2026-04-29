"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { getNodeEntry } from "../../nodes/registry";
import type { NodeData } from "../../nodes/types";
import { useWorkflowEditorStore } from "../../stores/workflowEditorStore";
import { useExecuteNode, useWorkflowRuns } from "../../hooks/useWorkflows";
import { resolveNodeInput } from "../../lib/node-io";
import type { NodeExecutionLog, WorkflowRun } from "../../types";
import { NDVHeader } from "./NDVHeader";
import { InputPanel } from "./InputPanel";
import { OutputPanel } from "./OutputPanel";
import { NodeSettingsPanel } from "./NodeSettingsPanel";

// Default ratio: Input 2/5 (40%) | Settings 1/5 (20%) | Output 2/5 (40%)
const DEFAULT_LEFT_PERCENT = 40;
const DEFAULT_RIGHT_PERCENT = 40;
const MIN_PANEL_WIDTH = 200;

interface NDVModalProps {
  workflowId: string;
}

export function NDVModal({ workflowId }: NDVModalProps) {
  const nodes = useWorkflowEditorStore((s) => s.nodes);
  const edges = useWorkflowEditorStore((s) => s.edges);
  const editingNodeId = useWorkflowEditorStore((s) => s.editingNodeId);
  const editNode = useWorkflowEditorStore((s) => s.editNode);
  const updateNodeData = useWorkflowEditorStore((s) => s.updateNodeData);

  const { data: runs } = useWorkflowRuns(workflowId, 20);
  // Latest *full* run is what NDV reads — partial runs (Execute step) overwrite
  // a single node's exec, so we treat them the same: the most-recent run that
  // mentions this node wins.
  const latestRun = runs?.[0] ?? null;
  const executeNode = useExecuteNode(workflowId);

  const node = nodes.find((n) => n.id === editingNodeId);
  const isOpen = !!node && !!editingNodeId;
  const entry = node ? getNodeEntry(node.data.nodeType as string) : null;
  const typeDef = entry?.definition ?? null;
  const nodeData = node?.data as unknown as NodeData | undefined;

  const io = useMemo(
    () => deriveNodeIO(latestRun, editingNodeId),
    [latestRun, editingNodeId],
  );

  const isPinned = useMemo(() => {
    const cfg = nodeData?.config as { _pinned_output?: unknown } | undefined;
    return Array.isArray(cfg?._pinned_output);
  }, [nodeData]);

  // --- Resizable panels (percentage-based) ---
  const containerRef = useRef<HTMLDivElement>(null);
  const [leftPercent, setLeftPercent] = useState(DEFAULT_LEFT_PERCENT);
  const [rightPercent, setRightPercent] = useState(DEFAULT_RIGHT_PERCENT);
  const draggingRef = useRef<"left" | "right" | null>(null);

  useEffect(() => {
    if (isOpen) {
      setLeftPercent(DEFAULT_LEFT_PERCENT);
      setRightPercent(DEFAULT_RIGHT_PERCENT);
    }
  }, [editingNodeId, isOpen]);

  const handleMouseDown = useCallback((side: "left" | "right") => {
    draggingRef.current = side;
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!draggingRef.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const totalWidth = rect.width;

      if (draggingRef.current === "left") {
        const px = Math.max(MIN_PANEL_WIDTH, e.clientX - rect.left);
        const pct = Math.min((px / totalWidth) * 100, 100 - rightPercent - 15);
        setLeftPercent(pct);
      } else {
        const px = Math.max(MIN_PANEL_WIDTH, rect.right - e.clientX);
        const pct = Math.min((px / totalWidth) * 100, 100 - leftPercent - 15);
        setRightPercent(pct);
      }
    };

    const handleMouseUp = () => {
      draggingRef.current = null;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [leftPercent, rightPercent]);

  const handleClose = useCallback(() => {
    editNode(null);
  }, [editNode]);

  const handleExecuteStep = useCallback(() => {
    if (!editingNodeId) return;
    const resolved = resolveNodeInput(latestRun, editingNodeId, nodes, edges);
    executeNode.mutate({
      nodeId: editingNodeId,
      input: { input_items: resolved.items },
    });
  }, [editingNodeId, latestRun, nodes, edges, executeNode]);

  const handleTogglePin = useCallback(() => {
    if (!editingNodeId || !nodeData) return;
    const cfg = (nodeData.config ?? {}) as Record<string, unknown>;

    if (isPinned) {
      // Drop the key entirely so saved configs stay clean.
      const { _pinned_output: _omit, ...rest } = cfg;
      void _omit;
      updateNodeData(editingNodeId, { config: rest });
      return;
    }

    if (io.kind !== "ready" || !io.exec.output_items?.length) return;
    updateNodeData(editingNodeId, {
      config: { ...cfg, _pinned_output: io.exec.output_items },
    });
  }, [editingNodeId, nodeData, isPinned, io, updateNodeData]);

  // Submit Execute step on ⌘/Ctrl + Enter while NDV is open.
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (!executeNode.isPending) handleExecuteStep();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, executeNode.isPending, handleExecuteStep]);

  if (!isOpen || !typeDef || !nodeData || !editingNodeId) return null;

  const exec = io.kind === "ready" ? io.exec : null;
  const inputState = io.kind === "no-run" ? "no-run" : io.kind === "not-reached" ? "not-reached" : "ready";
  const outputState =
    exec?.status === "running"
      ? "running"
      : io.kind === "no-run"
        ? "no-run"
        : io.kind === "not-reached"
          ? "not-reached"
          : "ready";

  const pinDisabledReason = !exec?.output_items?.length
    ? "Run this node first to pin its output"
    : undefined;

  return (
    <DialogPrimitive.Root open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0" />

        <DialogPrimitive.Content
          className="fixed inset-4 z-50 flex flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-[0.98] data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-[0.98]"
          onEscapeKeyDown={handleClose}
        >
          <DialogPrimitive.Title className="sr-only">
            {(nodeData.label || typeDef.label)} — Node Editor
          </DialogPrimitive.Title>

          <NDVHeader
            definition={typeDef}
            label={nodeData.label}
            onClose={handleClose}
            status={exec?.status}
            durationMs={exec ? execDurationMs(exec) : undefined}
            tokensUsed={exec?.tokens_used}
            onExecuteStep={handleExecuteStep}
            isExecuting={executeNode.isPending}
            isPinned={isPinned}
            onTogglePin={handleTogglePin}
            pinDisabledReason={pinDisabledReason}
          />

          <div ref={containerRef} className="flex flex-1 overflow-hidden">
            <div
              className="shrink-0 overflow-hidden border-r border-border bg-card"
              style={{ width: `${leftPercent}%` }}
            >
              <InputPanel items={exec?.input_items ?? null} state={inputState} />
            </div>

            <div
              className="group relative w-1 cursor-col-resize shrink-0 hover:bg-primary/20 active:bg-primary/30 transition-colors"
              onMouseDown={() => handleMouseDown("left")}
            >
              <div className="absolute inset-y-0 -left-0.5 -right-0.5" />
            </div>

            <div className="flex-1 overflow-hidden">
              <NodeSettingsPanel nodeId={editingNodeId} data={nodeData} />
            </div>

            <div
              className="group relative w-1 cursor-col-resize shrink-0 hover:bg-primary/20 active:bg-primary/30 transition-colors"
              onMouseDown={() => handleMouseDown("right")}
            >
              <div className="absolute inset-y-0 -left-0.5 -right-0.5" />
            </div>

            <div
              className="shrink-0 overflow-hidden border-l border-border bg-card"
              style={{ width: `${rightPercent}%` }}
            >
              <OutputPanel
                items={exec?.output_items ?? null}
                state={outputState}
                error={exec?.error ?? null}
              />
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

type NodeIO =
  | { kind: "no-run" }
  | { kind: "not-reached" }
  | { kind: "ready"; exec: NodeExecutionLog };

function deriveNodeIO(run: WorkflowRun | null, nodeId: string | null): NodeIO {
  if (!run || !nodeId) return { kind: "no-run" };
  const exec = run.node_executions.find((e) => e.node_id === nodeId);
  if (!exec) return { kind: "not-reached" };
  return { kind: "ready", exec };
}

function execDurationMs(exec: NodeExecutionLog): number | undefined {
  if (!exec.started_at || !exec.completed_at) return undefined;
  return new Date(exec.completed_at).getTime() - new Date(exec.started_at).getTime();
}
