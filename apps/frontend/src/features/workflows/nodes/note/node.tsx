"use client";

import { NodeResizer } from "@xyflow/react";
import { useNodeConfig } from "../../hooks/useNodeConfig";
import type { NodeContentProps } from "../types";

const MIN_W = 160;
const MIN_H = 80;
const DEFAULT_W = 240;
const DEFAULT_H = 140;

/**
 * Sticky-note layout: rendered *instead* of BaseNode (no shell, no handles).
 * The note is resizable when selected and edits content inline; nothing about
 * it participates in workflow execution.
 */
export default function NoteContent({ id, data, selected }: NodeContentProps & { selected?: boolean }) {
  const { config, updateConfig } = useNodeConfig(id);
  const content = (config.content as string) ?? "";

  return (
    <div
      className="relative h-full w-full rounded-md border border-amber-300/60 bg-amber-100 p-3 shadow-sm dark:border-amber-500/30 dark:bg-amber-500/15"
      style={{ minWidth: MIN_W, minHeight: MIN_H, width: DEFAULT_W, height: DEFAULT_H }}
    >
      <NodeResizer
        nodeId={id}
        isVisible={!!selected}
        minWidth={MIN_W}
        minHeight={MIN_H}
        color="#f59e0b"
      />
      <textarea
        value={content}
        onChange={(e) => updateConfig("content", e.target.value)}
        placeholder="Add a note…"
        spellCheck={false}
        className="h-full w-full resize-none border-none bg-transparent p-0 text-xs leading-relaxed text-amber-900 placeholder:text-amber-700/40 focus:outline-none dark:text-amber-100 dark:placeholder:text-amber-200/40"
        // Drag the canvas with the textarea unfocused; once focused the user
        // is editing, so block xyflow's drag handler from stealing keystrokes.
        onPointerDown={(e) => e.stopPropagation()}
      />
      {/* Keep id readable in tests but not visually noisy */}
      <span className="sr-only">{data.label}</span>
    </div>
  );
}
