"use client";

import { Save, Play, ZoomIn, ZoomOut, Maximize2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkflowEditorStore } from "../stores/workflowEditorStore";

interface WorkflowToolbarProps {
  onSave: () => void;
  onRun: () => void;
  isSaving: boolean;
  workflowName: string;
}

export function WorkflowToolbar({
  onSave,
  onRun,
  isSaving,
}: WorkflowToolbarProps) {
  const isDirty = useWorkflowEditorStore((s) => s.isDirty);

  return (
    <div className="flex items-center gap-1.5">
      <Button
        onClick={onRun}
        variant="outline"
        size="sm"
        className="gap-1.5"
      >
        <Play className="h-3 w-3" />
        Run
      </Button>

      <Button
        onClick={onSave}
        disabled={isSaving || !isDirty}
        size="sm"
        className="gap-1.5"
      >
        {isSaving ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Save className="h-3 w-3" />
        )}
        Save
      </Button>
    </div>
  );
}
