"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { getNodeEntry } from "../../nodes/registry";
import type { NodeData } from "../../nodes/types";
import { useWorkflowEditorStore } from "../../stores/workflowEditorStore";
import { NDVHeader } from "./NDVHeader";
import { InputPanel } from "./InputPanel";
import { OutputPanel } from "./OutputPanel";
import { NodeSettingsPanel } from "./NodeSettingsPanel";

// Default ratio: Input 2/5 (40%) | Settings 1/5 (20%) | Output 2/5 (40%)
const DEFAULT_LEFT_PERCENT = 40;
const DEFAULT_RIGHT_PERCENT = 40;
const MIN_PANEL_WIDTH = 200;

export function NDVModal() {
  const { nodes, editingNodeId, editNode } = useWorkflowEditorStore();

  const node = nodes.find((n) => n.id === editingNodeId);
  const isOpen = !!node && !!editingNodeId;
  const entry = node ? getNodeEntry(node.data.nodeType as string) : null;
  const typeDef = entry?.definition ?? null;
  const nodeData = node?.data as unknown as NodeData | undefined;

  // --- Resizable panels (percentage-based) ---
  const containerRef = useRef<HTMLDivElement>(null);
  const [leftPercent, setLeftPercent] = useState(DEFAULT_LEFT_PERCENT);
  const [rightPercent, setRightPercent] = useState(DEFAULT_RIGHT_PERCENT);
  const draggingRef = useRef<"left" | "right" | null>(null);

  // Reset to defaults when opening a new node
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

  if (!isOpen || !typeDef || !nodeData || !editingNodeId) return null;

  return (
    <DialogPrimitive.Root open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogPrimitive.Portal>
        {/* Overlay */}
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0" />

        {/* Content — full screen with margin */}
        <DialogPrimitive.Content
          className="fixed inset-4 z-50 flex flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-[0.98] data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-[0.98]"
          onEscapeKeyDown={handleClose}
        >
          {/* Visually hidden title for accessibility */}
          <DialogPrimitive.Title className="sr-only">
            {(nodeData.label || typeDef.label)} — Node Editor
          </DialogPrimitive.Title>

          {/* Header */}
          <NDVHeader
            definition={typeDef}
            label={nodeData.label}
            onClose={handleClose}
          />

          {/* 3-panel body */}
          <div ref={containerRef} className="flex flex-1 overflow-hidden">
            {/* INPUT panel */}
            <div
              className="shrink-0 overflow-hidden border-r border-border bg-card"
              style={{ width: `${leftPercent}%` }}
            >
              <InputPanel items={[]} />
            </div>

            {/* Left resize handle */}
            <div
              className="group relative w-1 cursor-col-resize shrink-0 hover:bg-primary/20 active:bg-primary/30 transition-colors"
              onMouseDown={() => handleMouseDown("left")}
            >
              <div className="absolute inset-y-0 -left-0.5 -right-0.5" />
            </div>

            {/* SETTINGS panel (center, takes remaining space) */}
            <div className="flex-1 overflow-hidden">
              <NodeSettingsPanel nodeId={editingNodeId} data={nodeData} />
            </div>

            {/* Right resize handle */}
            <div
              className="group relative w-1 cursor-col-resize shrink-0 hover:bg-primary/20 active:bg-primary/30 transition-colors"
              onMouseDown={() => handleMouseDown("right")}
            >
              <div className="absolute inset-y-0 -left-0.5 -right-0.5" />
            </div>

            {/* OUTPUT panel */}
            <div
              className="shrink-0 overflow-hidden border-l border-border bg-card"
              style={{ width: `${rightPercent}%` }}
            >
              <OutputPanel items={[]} />
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
