"use client";

import { useState } from "react";
import {
  Play,
  Save,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { useTool, useUpdateTool, useTestTool } from "../hooks/useTools";
import { TOOL_TYPE_META } from "../types";
import { cn } from "@/lib/utils";

interface ToolDetailSheetProps {
  toolId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ToolDetailSheet({ toolId, open, onOpenChange }: ToolDetailSheetProps) {
  const { data: tool, isLoading } = useTool(toolId);
  const updateTool = useUpdateTool(toolId);
  const testTool = useTestTool();
  const [testInput, setTestInput] = useState('{"query": "test"}');

  if (isLoading || !tool) {
    return (
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="bg-card border-border text-foreground w-[480px] sm:max-w-[480px]">
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        </SheetContent>
      </Sheet>
    );
  }

  const meta = TOOL_TYPE_META[tool.tool_type];

  const handleSave = (field: string, value: unknown) => {
    updateTool.mutate({ [field]: value });
  };

  const handleTest = () => {
    try {
      const parsed = JSON.parse(testInput);
      testTool.mutate({ id: toolId, inputData: parsed });
    } catch {
      // Invalid JSON
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="bg-card border-border text-foreground w-[480px] sm:max-w-[480px] overflow-auto">
        <SheetHeader>
          <div className="flex items-center gap-3">
            <SheetTitle className="text-foreground">{tool.name}</SheetTitle>
            <Badge
              variant="secondary"
              className="text-[10px] px-1.5 h-5 bg-muted text-muted-foreground"
            >
              {meta?.label}
            </Badge>
          </div>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Name */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-muted-foreground">Name</label>
            <Input
              defaultValue={tool.name}
              onBlur={(e) => handleSave("name", e.target.value)}
              className="h-8 bg-muted border-border text-sm"
            />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-muted-foreground">
              Description <span className="text-muted-foreground">(LLM sees this)</span>
            </label>
            <Textarea
              defaultValue={tool.description}
              onBlur={(e) => handleSave("description", e.target.value)}
              className="min-h-[60px] bg-muted border-border text-sm"
            />
          </div>

          {/* Config (JSON editor) */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-muted-foreground">Configuration</label>
            <Textarea
              defaultValue={JSON.stringify(tool.config, null, 2)}
              onBlur={(e) => {
                try {
                  handleSave("config", JSON.parse(e.target.value));
                } catch { /* invalid json */ }
              }}
              className="min-h-[120px] bg-muted border-border text-xs font-mono"
            />
          </div>

          {/* Input Schema */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-muted-foreground">Input Schema</label>
            <Textarea
              defaultValue={JSON.stringify(tool.input_schema, null, 2)}
              onBlur={(e) => {
                try {
                  handleSave("input_schema", JSON.parse(e.target.value));
                } catch { /* invalid json */ }
              }}
              className="min-h-[80px] bg-muted border-border text-xs font-mono"
            />
          </div>

          {/* Timeout */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-muted-foreground">Timeout (seconds)</label>
            <Input
              type="number"
              defaultValue={tool.timeout_seconds}
              onBlur={(e) => handleSave("timeout_seconds", Number(e.target.value))}
              className="h-8 w-32 bg-muted border-border text-sm"
            />
          </div>

          {/* Divider */}
          <div className="h-px bg-muted" />

          {/* Test tool */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-foreground/70">Test Tool</label>
            <Textarea
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
              placeholder='{"query": "test input"}'
              className="min-h-[60px] bg-muted border-border text-xs font-mono"
            />
            <Button
              onClick={handleTest}
              disabled={testTool.isPending}
              size="sm"
              variant="outline"
              className="gap-1.5 border-border bg-muted"
            >
              {testTool.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Play className="h-3 w-3" />
              )}
              Run Test
            </Button>

            {/* Test result */}
            {testTool.data && (
              <div
                className={cn(
                  "rounded-lg border p-3",
                  testTool.data.success
                    ? "border-emerald-500/20 bg-emerald-500/5"
                    : "border-red-500/20 bg-red-500/5"
                )}
              >
                <div className="flex items-center gap-2 mb-2">
                  {testTool.data.success ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-red-400" />
                  )}
                  <span className="text-xs font-medium">
                    {testTool.data.success ? "Success" : "Failed"}
                  </span>
                  <span className="ml-auto flex items-center gap-1 text-[10px] text-muted-foreground">
                    <Clock className="h-2.5 w-2.5" />
                    {testTool.data.latency_ms}ms
                  </span>
                </div>
                <pre className="text-[11px] text-muted-foreground font-mono whitespace-pre-wrap break-all max-h-[200px] overflow-auto">
                  {testTool.data.result || testTool.data.error}
                </pre>
              </div>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
