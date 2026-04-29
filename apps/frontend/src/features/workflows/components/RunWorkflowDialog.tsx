"use client";

import { useEffect, useMemo, useState } from "react";
import { Loader2, Play, AlertTriangle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface RunWorkflowDialogProps {
  workflowId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRun: (input: Record<string, unknown>) => void;
  isRunning?: boolean;
}

const DEFAULT_INPUT = `{\n  "message": "Hello"\n}`;

function storageKey(workflowId: string) {
  return `wf:lastInput:${workflowId}`;
}

export function RunWorkflowDialog({
  workflowId,
  open,
  onOpenChange,
  onRun,
  isRunning = false,
}: RunWorkflowDialogProps) {
  const [text, setText] = useState(DEFAULT_INPUT);

  // Restore last-used input when the dialog opens.
  useEffect(() => {
    if (!open) return;
    const stored = typeof window !== "undefined"
      ? window.localStorage.getItem(storageKey(workflowId))
      : null;
    setText(stored || DEFAULT_INPUT);
  }, [open, workflowId]);

  const parseError = useMemo(() => {
    if (!text.trim()) return "Input cannot be empty";
    try {
      const parsed = JSON.parse(text);
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        return "Input must be a JSON object";
      }
      return null;
    } catch (e) {
      return e instanceof Error ? e.message : "Invalid JSON";
    }
  }, [text]);

  const handleRun = () => {
    if (parseError) return;
    const parsed = JSON.parse(text) as Record<string, unknown>;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(storageKey(workflowId), text);
    }
    onRun(parsed);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Run workflow</DialogTitle>
          <DialogDescription>
            Provide the input data passed to the start node. Must be a JSON object.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <label htmlFor="run-input" className="text-xs font-medium text-muted-foreground">
            Input data
          </label>
          <textarea
            id="run-input"
            spellCheck={false}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                handleRun();
              }
            }}
            className={cn(
              "min-h-40 w-full resize-y rounded-md border bg-muted/30 px-3 py-2 font-mono text-xs outline-none focus:border-primary focus:ring-1 focus:ring-primary/30",
              parseError ? "border-red-500/40" : "border-border",
            )}
          />
          {parseError && (
            <div className="flex items-start gap-1.5 text-[11px] text-red-600 dark:text-red-400">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
              <span>{parseError}</span>
            </div>
          )}
          <p className="text-[10px] text-muted-foreground">
            Press <kbd className="rounded border border-border bg-muted px-1">⌘</kbd>+
            <kbd className="rounded border border-border bg-muted px-1">Enter</kbd> to run.
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isRunning}>
            Cancel
          </Button>
          <Button onClick={handleRun} disabled={!!parseError || isRunning} className="gap-1.5">
            {isRunning ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Run
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
