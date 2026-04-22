"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import { getNodeEntry } from "../nodes/registry";
import { NDVHeader } from "./ndv/NDVHeader";
import { InputPanel } from "./ndv/InputPanel";
import { OutputPanel } from "./ndv/OutputPanel";

interface NodeExecution {
  node_id: string;
  node_type: string;
  label: string | null;
  status: string;
  input_items: unknown;
  output_items: unknown;
  error: string | null;
  tokens_used: number;
  started_at: string | null;
  completed_at: string | null;
}

interface ExecutionNDVModalProps {
  execution: NodeExecution | null;
  open: boolean;
  onClose: () => void;
}

const DEFAULT_LEFT_PERCENT = 50;
const MIN_PANEL_WIDTH = 200;

/** Normalise input/output — the backend stores either a single dict or a list of
 *  items. The InputPanel/OutputPanel expect `Record<string, unknown>[]`. */
function toItems(data: unknown): Record<string, unknown>[] {
  if (data == null) return [];
  if (Array.isArray(data)) return data as Record<string, unknown>[];
  if (typeof data === "object") return [data as Record<string, unknown>];
  return [{ value: data as unknown } as Record<string, unknown>];
}

/**
 * Read-only NDV shown from the Executions view.
 * Two panels: INPUT | OUTPUT, side by side, resizable.
 */
export function ExecutionNDVModal({ execution, open, onClose }: ExecutionNDVModalProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [leftPercent, setLeftPercent] = useState(DEFAULT_LEFT_PERCENT);
  const draggingRef = useRef(false);

  useEffect(() => {
    if (open) setLeftPercent(DEFAULT_LEFT_PERCENT);
  }, [open, execution?.node_id]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!draggingRef.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const px = Math.max(
        MIN_PANEL_WIDTH,
        Math.min(rect.width - MIN_PANEL_WIDTH, e.clientX - rect.left),
      );
      setLeftPercent((px / rect.width) * 100);
    };
    const handleMouseUp = () => {
      draggingRef.current = false;
    };
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  const handleClose = useCallback(() => onClose(), [onClose]);

  const definition = useMemo(
    () => (execution ? getNodeEntry(execution.node_type)?.definition ?? null : null),
    [execution],
  );

  if (!open || !execution || !definition) return null;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0" />

        <DialogPrimitive.Content
          className="fixed inset-4 z-50 flex flex-col overflow-hidden rounded-xl border border-border bg-background shadow-2xl outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-[0.98] data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-[0.98]"
          onEscapeKeyDown={handleClose}
        >
          <DialogPrimitive.Title className="sr-only">
            {(execution.label || definition.label)} — Execution Detail
          </DialogPrimitive.Title>

          <NDVHeader
            definition={definition}
            label={execution.label ?? ""}
            onClose={handleClose}
          />

          <div ref={containerRef} className="flex flex-1 overflow-hidden">
            <div
              className="shrink-0 overflow-hidden border-r border-border bg-card"
              style={{ width: `${leftPercent}%` }}
            >
              <InputPanel items={toItems(execution.input_items)} />
            </div>

            <div
              className="group relative w-1 cursor-col-resize shrink-0 hover:bg-primary/20 active:bg-primary/30 transition-colors"
              onMouseDown={() => {
                draggingRef.current = true;
              }}
            >
              <div className="absolute inset-y-0 -left-0.5 -right-0.5" />
            </div>

            <div className="flex-1 overflow-hidden bg-card">
              {execution.error ? (
                <div className="flex h-full flex-col">
                  <div className="border-b border-border px-4 py-2.5">
                    <span className="text-xs font-semibold tracking-wider text-red-600 dark:text-red-400">
                      ERROR
                    </span>
                  </div>
                  <pre className="m-4 whitespace-pre-wrap rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-500/20 dark:bg-red-500/5 dark:text-red-300">
                    {execution.error}
                  </pre>
                </div>
              ) : (
                <OutputPanel items={toItems(execution.output_items)} />
              )}
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
